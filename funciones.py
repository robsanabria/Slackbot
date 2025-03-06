import os
import re
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta
import openai
from openai.error import OpenAIError
from fuzzywuzzy import process

# Load environment variables from a .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# MongoDB credentials
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")
MONGO_CONN_STRING = os.getenv("MONGO_CONN_STRING")

# Initialize MongoDB client
client = MongoClient(MONGO_CONN_STRING, username=MONGO_USER, password=MONGO_PASS)
db = client.Configuration_db  # Connect to the database
locations_collection = db.Locations  # Access the Locations collection

# OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set the OpenAI API key
openai.api_key = OPENAI_API_KEY

def generate_openai_response(message):
    try:
        response = openai_client.completions.create(
            model="gpt-3.5-turbo-instruct",  # Use the appropriate model
            prompt=message,
            max_tokens=150,  # Adjust the number of tokens based on your requirements
            n=1,
            stop=None,
            temperature=0.7  # Adjust the temperature for creativity level
        )
        
        # Extract and return the text from the response
        return response['choices'][0]['text'].strip()
    except (APIError, APIConnectionError, AuthenticationError, RateLimitError) as e:
        # Handle specific OpenAI errors
        return f"An OpenAI API error occurred: {str(e)}"
    except OpenAIError as e:
        # Handle general OpenAI errors
        return f"An error occurred with the OpenAI API: {str(e)}"
    except Exception as e:
        # Handle other possible errors
        return f"An unexpected error occurred: {str(e)}"

def get_toast_config(restaurant_name):
    client = MongoClient("mongodb+srv://robert:whVD6oCf3bIM7J38@sauce-prod.upwt6.mongodb.net/")
    db = client["Configuration_db"]
    collection = db["Locations"]
    
    # Find the restaurant document
    restaurant = collection.find_one({"FullName": restaurant_name})
    
    if not restaurant:
        return f"No configuration found for restaurant '{restaurant_name}'."
    
    # Find the Toast configuration
    toast_config = next((config for config in restaurant.get("ThirdPartyConfigs", []) if config.get("Type") == "Toast"), None)
    
    if not toast_config:
        return f"No Toast configuration found for restaurant '{restaurant_name}'."
    
    # Structured format for the response
    response = f"*Toast Configuration for '{restaurant_name}':*\n"
    
    # Details of the Toast configuration
    response += "• *Active*: " + ("Yes" if toast_config.get("Active", False) else "No") + "\n"
    response += "• Type: " + toast_config.get("Type", "N/A") + "\n"
    response += "• *Visibility:* " + toast_config.get("VisibilityType", "N/A") + "\n"
    response += "• Discount Name: " + toast_config.get("DiscountName", "N/A") + "\n"
    response += "• Revenue Center Id: " + toast_config.get("RevenueCenterId", "N/A") + "\n\n"
    
    # Service Name Configuration
    response += "*Service Name Configuration:*\n"
    response += "• Pickup Dining: " + toast_config.get("PickupDiningName", "N/A") + "\n"
    response += "• Dine In Dining: " + toast_config.get("DineInDiningName", "N/A") + "\n"
    response += "• Delivery Dining: " + toast_config.get("DeliveryDiningName", "N/A") + "\n"
    response += "• Credit Payment: " + toast_config.get("CreditPaymentName", "N/A") + "\n"
    response += "• Delivery Provider (Uber): " + toast_config.get("UberCreditPaymentName", "N/A") + "\n\n"
    
    # Other Configurations
    response += "*Other Configurations:*\n"
    response += "• Update Menu on Provider Change: " + ("Yes" if toast_config.get("UpdateMenuProviderOnChange", False) else "No") + "\n"
    response += "• Is Main Provider: " + ("Yes" if toast_config.get("IsMainProvider", False) else "No") + "\n"
    response += "• Need to Send SMS: " + ("Yes" if toast_config.get("NeedSendSms", False) else "No") + "\n"
    response += "• Notes as Item: " + ("Yes" if toast_config.get("SendNotesAsItem", False) else "No") + "\n"
    
    return response


# Function to fetch opening hours based on restaurant name
def get_opening_hours(restaurant_name):
    try:
        # Query MongoDB to find the restaurant by FullName
        restaurant = locations_collection.find_one({"FullName": restaurant_name})
        if not restaurant:
            return f"Oops! I couldn't find any restaurant named '{restaurant_name}'. Please double-check the name or let me know if you need help!"

        opening_hours = restaurant.get("OpeningHours")
        if not opening_hours:
            return f"It seems we don't have opening hours available for '{restaurant_name}'. Let me know if there's anything else I can assist with!"

        # Prepare the formatted hours
        days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        formatted_hours = []

        for i, hours_info in enumerate(opening_hours):
            start_time = hours_info.get("Start")
            duration = hours_info.get("Duration")
            
            if start_time is None or duration is None:
                logger.warning(f"Missing Start or Duration for {restaurant_name} on {days_of_week[i % 7]}: {hours_info}")
                continue

            try:
                # Calculate start and end times
                start_hour, start_minute = divmod(start_time % 1440, 60)
                end_hour, end_minute = divmod((start_time + duration) % 1440, 60)
                day_of_week = days_of_week[i % 7]
                formatted_hours.append(f"{day_of_week}: {start_hour:02}:{start_minute:02} - {end_hour:02}:{end_minute:02}")
            except Exception as calc_error:
                logger.error(f"Error calculating times for {restaurant_name} on {days_of_week[i % 7]}: {calc_error}")
                continue

        if formatted_hours:
            # Add a friendly intro and closing message
            intro_message = f"Here are the opening hours for *{restaurant_name}* 😊 : \n"
            closing_message = "\nLet me know if you need anything else or have any questions!"
            return intro_message + "\n".join(formatted_hours) + closing_message
        else:
            return f"It seems we couldn't process the opening hours for '{restaurant_name}'. Let me know if you'd like me to check again!"

    except PyMongoError as e:
        logger.error(f"Error fetching opening hours from MongoDB: {e}")
        return "An internal error occurred while fetching opening hours. Please try again later. 🙁"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "An unexpected error occurred. Please try again later. 🙁"

def get_delivery_settings(restaurant_name):
    try:
        # Query MongoDB to find the restaurant by FullName
        restaurant = locations_collection.find_one({"FullName": restaurant_name})
        if restaurant:
            delivery_settings = restaurant.get("Delivery", [])
            if delivery_settings:
                minimal_order = delivery_settings[0].get("MinimalOrder", "Not specified")
                delivery_price = delivery_settings[0].get("DeliveryPrice", "Not specified")
                delivery_fee = delivery_settings[0].get("DeliverySay2eatFee", "Not specified")
                radial_area = delivery_settings[0].get("RadialDeliveryArea", "Not specified")
                polygon_area = delivery_settings[0].get("PolygonDeliveryArea", [])
                
                # Format response
                response = f"Delivery settings for {restaurant_name}:\n"
                response += f"• Minimal Order: {minimal_order}\n"
                response += f"• Delivery Price: {delivery_price}\n"
                response += f"• Delivery Say2eat Fee: {delivery_fee}\n"
                response += f"• Radial Delivery Area: {radial_area}\n"
                if polygon_area:
                    response += "• Polygon Delivery Area:\n"
                    for point in polygon_area:
                        response += f"  - Latitude: {point.get('Latitude')}, Longitude: {point.get('Longitude')}\n"
                return response
            else:
                return "Delivery settings not available."
        else:
            return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the Restaurant"
    except PyMongoError as e:
        logger.error(f"Error fetching delivery settings from MongoDB: {e}")
        return "An error occurred while fetching delivery settings."

def get_contact_info(restaurant_name: str) -> str:
    # Buscar el restaurante en la colección
    restaurant = locations_collection.find_one({"FullName": restaurant_name})
    
    # Verificar si el restaurante fue encontrado
    if not restaurant:
        return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the Restaurant."
    
    # Extraer la información de contacto
    phone = restaurant.get('Phone', 'N/A')
    address = restaurant.get('StructuredAddress', {}).get('FormattedAddress', 'N/A')
    google_map_url = restaurant.get('GoogleMapURL', 'N/A')
    website_url = restaurant.get('GmbRestaurantUrl', 'N/A')
    
    # Formatear la información de contacto
    contact_info = (
        f"Contact information for {restaurant_name}\n\n"
        f"• Phone: {phone}\n"
        f"• Address: {address}\n"
        f"• Google Maps URL: {google_map_url}\n"
        f"• Website URL: {website_url}"
    )
    
    return contact_info

def close_restaurant_manually(restaurant_name: str, reason: str = None, until_time: datetime = None) -> str:
    try:
        # Buscar el restaurante en la colección
        restaurant = locations_collection.find_one({"FullName": restaurant_name})
        
        if not restaurant:
            return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the Restaurant."
        
        # Verificar si el restaurante ya está cerrado manualmente
        if restaurant.get("ClosedManually", False):
            return f"Restaurant '{restaurant_name}' is already closed manually."

        # Establecer los valores de cierre manual
        update_fields = {
            "ClosedManually": True,
            "ClosedManuallyTime": datetime.utcnow(),
            "ClosedManuallyReason": reason,
            "ClosedManuallyUntilTime": until_time
        }
        
        # Actualizar el documento del restaurante
        locations_collection.update_one({"FullName": restaurant_name}, {"$set": update_fields})
        
        response = f"Done! Restaurant '{restaurant_name}' has been closed manually."
        if until_time:
            response += f" It will remain closed until {until_time}."
        if reason:
            response += f" Reason: {reason}."
        
        return response
    except PyMongoError as e:
        logger.error(f"Error closing restaurant manually in MongoDB: {e}")
        return "An error occurred while closing the restaurant manually."

def get_mail_for_human_response(restaurant_name: str) -> str:
    # Buscar el restaurante en la colección
    restaurant = locations_collection.find_one({"FullName": restaurant_name})
    
    print(f"Searching for restaurant: {restaurant_name}")  # Depuración
    
    # Verificar si el restaurante fue encontrado
    if not restaurant:
        return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the Restaurant."
    
    # Extraer el correo para respuesta humana
    mail = restaurant.get('MailForHumanResponseMessage', 'N/A')
    
    # Formatear la información del correo
    mail_info = (
        f"Mail for human response for {restaurant_name}\n\n"
        f"• Mail: {mail}"
    )
    
    return mail_info

def get_stripe_info(restaurant_name: str) -> str:
    # Buscar el restaurante en la colección
    restaurant = locations_collection.find_one({"FullName": restaurant_name})
    
    # Verificar si el restaurante fue encontrado
    if not restaurant:
        return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the Restaurant."
    
    # Extraer StripeID y StripeCustomerId
    stripe_id = restaurant.get('StripeManagedAccountLive', 'N/A')  # Stripe ID
    stripe_customer_id = restaurant.get('StripeCustomerId', 'N/A')  # Stripe Customer ID
    
    # Formatear la información
    stripe_info = (
        f"Stripe Info for {restaurant_name}\n\n"
        f"• Stripe ID: {stripe_id}\n"
        f"• Stripe Customer ID (Chartmogul): {stripe_customer_id}"
    )
    
    return stripe_info

def get_delivery_options(restaurant_name: str) -> str:
    # Buscar el restaurante en la colección
    restaurant = locations_collection.find_one({"FullName": restaurant_name})
    
    # Verificar si el restaurante fue encontrado
    if not restaurant:
        return f"Restaurant '{restaurant_name}' not found. Please make sure you are writing the full name of the restaurant."
    
    # Obtener las opciones de entrega
    delivery_options = restaurant.get("DeliveryOptions", {})
    
    # Formatear la información de las opciones de entrega
    if not delivery_options:
        return f"No delivery options available for {restaurant_name}."
    
    delivery_info = (
        f"Delivery options for {restaurant_name}:\n\n"
        f"• Delivery: {delivery_options.get('Delivery', 'N/A')}\n"
        f"• Pickup: {delivery_options.get('Pickup', 'N/A')}\n"
        f"• Catering: {delivery_options.get('IsCatering', 'N/A')}\n"
        f"• Curbside: {delivery_options.get('Curbside', 'N/A')}\n"
        f"• Dine-in: {delivery_options.get('DineIn', 'N/A')}"
    )
    
    return delivery_info

def get_coupon_usage_count(coupon_code: str) -> int:
    # Convertir el código de cupón a minúsculas
    coupon_code_lower = coupon_code.lower()
    print(f"Searching for coupon (case-insensitive): {coupon_code_lower}")
    
    client = MongoClient("mongodb+srv://robert:whVD6oCf3bIM7J38@sauce-prod.upwt6.mongodb.net/")
    try:
        db = client.get_database('Users')
        collection = db.get_collection('UsersOrders')

        pipeline = [
            {
                "$match": {
                    "Payment.CouponCode": {
                        "$regex": f"^{coupon_code_lower}$",  # Busca exactamente el código, ignorando mayúsculas/minúsculas
                        "$options": "i"  # Opción para ignorar mayúsculas/minúsculas
                    }
                }
            },
            {"$count": "coupon_usage_count"}
        ]

        print(f"Pipeline: {pipeline}")
        result = list(collection.aggregate(pipeline))
        print(f"Aggregation result: {result}")

        if result:
            count = result[0].get("coupon_usage_count", 0)
            print(f"Coupon usage count for '{coupon_code_lower}': {count}")
        else:
            print(f"No documents matched the coupon code: {coupon_code_lower}")
            count = 0

        return count

    except Exception as e:
        print(f"Error during aggregation: {e}")
        return 0

    finally:
        client.close()

def handle_coupon_usage(query: str) -> str:
    """
    Handle the user query about coupon usage.
    Args:
        query (str): The user query asking about coupon usage.
    Returns:
        str: A response message with the coupon usage count.
    """
    try:
        # Usa expresión regular para extraer el código de cupón
        match = re.search(r"(?i)How many times was the (\w+) used", query)

        if match:
            coupon_code = match.group(1).strip().lower()  # Extraemos y formateamos el código de cupón
            print(f"Extracted coupon code: {coupon_code}")  # Log para verificar
        else:
            return "Coupon code not found in the query. Please provide a valid coupon code."

        # Llama a la función para obtener el conteo
        usage_count = get_coupon_usage_count(coupon_code)

        # Genera la respuesta basada en el resultado
        if usage_count > 0:
            return f"The coupon code '{coupon_code}' has been used {usage_count} times."
        else:
            return f"The coupon code '{coupon_code}' has not been used yet."

    except Exception as e:
        print(f"Error handling coupon usage query: {e}")
        return "An error occurred while processing your request. Please try again later."

def process_slack_message(message):
    logger.debug(f"Processing message: {message}")

    # Patrones ajustados para usar "Please send" en lugar de "I need"
    patterns = {
        "test order": r'(?i)create a test order ticket for (.+)',
        "close restaurant": r'(?i)create a close restaurant ticket for (.+)',
        "open insights": r'(?i)create an open insights ticket for (.+)',
        "clarity check": r'(?i)create a clarity check ticket for (.+)',
        "delivery range": r'(?i)create a delivery range ticket for (.+)',
        "status of ticket": r'(?i)Please send the status of the ticket (RSC-\d+)',
        "opening hours": r'(?i)Please send opening hours from (.+)',
        "delivery settings": r'(?i)Please send delivery settings from (.+)',
        "contact info": r'(?i)Please send contact info from (.+)',
        "toast config": r'(?i)please send(?: the)? toast config from (.+)',
        "close manually": r'(?i)close manually (.+)',
        "mail for report": r'(?i)Please send mail for report from (.+)',
        "stripe info": r'(?i)Please send stripe info from (.+)',
        "delivery options": r'(?i)Please send delivery options from (.+)',  # Nueva clave
        "coupon usage": r'(?i)How many times was the (.+?) used'
    }

    # Lógica para procesar mensajes según el patrón encontrado
    for key, pattern in patterns.items():
        match = re.search(pattern, message)
        if match:
            # Casos específicos con funciones
            if key == "status of ticket":
                ticket_key = match.group(1)
                resolution_name = get_jira_ticket_resolution(ticket_key)
                return f"The resolution status of ticket {ticket_key} is: {resolution_name}"
            elif key == "opening hours":
                restaurant_name = match.group(1)
                response = get_opening_hours(restaurant_name)
                return response
            elif key == "delivery settings":
                restaurant_name = match.group(1)
                response = get_delivery_settings(restaurant_name)
                return response
            elif key == "contact info":
                restaurant_name = match.group(1)
                response = get_contact_info(restaurant_name)
                return response
            elif key == "toast config":
                restaurant_name = match.group(1)
                response = get_toast_config(restaurant_name)
                return response
            elif key == "close manually":
                restaurant_name = match.group(1)
                response = close_restaurant_manually(restaurant_name)
                return response
            elif key == "mail for report":
                restaurant_name = match.group(1)
                response = get_mail_for_human_response(restaurant_name)
                return response
            elif key == "stripe info":
                restaurant_name = match.group(1)
                response = get_stripe_info(restaurant_name)
                return response
            elif key == "delivery options":
                restaurant_name = match.group(1)
                response = get_delivery_options(restaurant_name)
                return response
            elif key == "coupon usage":
                coupon_code = match.group(1)
                usage_count = get_coupon_usage_count(coupon_code)  # Llamamos a la función para contar el uso del cupón
                return f"The coupon code '{coupon_code}' has been used {usage_count} times."


            # Casos relacionados con tickets de Jira
            restaurant_name = match.group(1)
            summary, description, issue_type = "", "", ""
            if key == "test order":
                summary = f"[Ordering] - Test Order for {restaurant_name}"
                description = f"This is a ticket created by Sassito to inform that a test order was performed for: {restaurant_name}."
                issue_type = "Task"
            elif key == "close restaurant":
                summary = f"[Store Settings] - Close {restaurant_name} from Admin"
                description = f"This is a ticket informing the closing of the restaurant: {restaurant_name}"
                issue_type = "Task"
            elif key == "open insights":
                summary = f"[Dashboard] - Open Insights for {restaurant_name}"
                description = f"This is a ticket to inform that we Open Insights for the restaurant: {restaurant_name}"
                issue_type = "Task"
            elif key == "clarity check":
                summary = f"[Dispatch] - Clarity Check for {restaurant_name}"
                description = f"This is a ticket to inform that a clarity check for the restaurant: {restaurant_name}"
                issue_type = "Task"
            elif key == "delivery range":
                summary = f"[Store Settings] - Information about delivery range of {restaurant_name}"
                description = f"This is a ticket to inform that we provide information about the delivery range of the restaurant: {restaurant_name}"
                issue_type = "Task"

            # Código para crear un ticket en Jira (comentado si no se usa)
            # issue_url = create_jira_ticket(summary, description, issue_type, key)
            # if issue_url:
            #     notify_slack_new_ticket(issue_url)
            #     return f"The ticket has been created in Jira. You can access the ticket here: {issue_url}"
            # else:
            #     return "An error occurred while creating the ticket in Jira."

    # Si no se encuentra coincidencia exacta, usar fuzzy matching
    matched_pattern = process.extractOne(message, patterns.keys(), score_cutoff=70)

    if matched_pattern:
        suggestion = (f"🤔 It seems like you're looking for something similar to:\n\n"
                  f"👉 *'Please send {matched_pattern[0]} from [restaurant_name]'*\n\n"
                  f"Please try rephrasing your request or confirm if this is what you meant!")
        return suggestion  # Este return debe estar correctamente indentado dentro del bloque if
    else:
        # Opciones disponibles si no se encuentra coincidencia
        available_options = "\n".join([f"{i+1}. {key.capitalize().replace('_', ' ')}" for i, key in enumerate(patterns.keys())])
        return (f"❓ I'm sorry, I didn't quite catch that. Here are some things I can help you with:\n\n"
            f"{available_options}\n\n"
            f"👉 *Example*: 'Please send opening hours from MyRestaurantName'\n\n"
            f"Let me know how I can assist you! 😊")

    # Si es necesario, fallback a OpenAI
    #return generate_openai_response(message)

def handle_unknown_command(client, channel, user, thread_ts, text):
    patterns = {
        "test order": r'(?i)create a test order ticket for (.+)',
        "close restaurant": r'(?i)create a close restaurant ticket for (.+)',
        "open insights": r'(?i)create an open insights ticket for (.+)',
        "clarity check": r'(?i)create a clarity check ticket for (.+)',
        "delivery range": r'(?i)create a delivery range ticket for (.+)',
        "status of ticket": r'(?i)Please send the status of the ticket (RSC-\d+)',
        "opening hours": r'(?i)Please send opening hours from (.+)',
        "delivery settings": r'(?i)Please send delivery settings from (.+)',
        "contact info": r'(?i)Please send contact info from (.+)',
        "toast config": r'(?i)Please send toast info from (.+)',
        "close manually": r'(?i)close manually (.+)',
        "mail for report": r'(?i)Please send mail for report from (.+)',
        "stripe info": r'(?i)Please send stripe info from (.+)',
        "delivery options": r'(?i)Please send delivery options from (.+)', # Nueva clave
        "coupon usage": r'(?i)How many times was the (.+?) used'
    }
    
    """
    Maneja comandos desconocidos proporcionando orientación dinámica con fuzzy matching.
    """
    # Utiliza fuzzy matching para encontrar un comando similar
    matched_pattern = process.extractOne(text, patterns.keys(), score_cutoff=70)

    # Preparar las respuestas dependiendo de si hay coincidencias o no
    if matched_pattern:
        suggestion = (f"🤔 It seems like you're looking for something similar to:\n\n"
                      f"👉 *'Please send {matched_pattern[0]} from [restaurant_name]'*\n\n"
                      f"Please try rephrasing your request or confirm if this is what you meant!")
    else:
        # Si no hay coincidencias, proporcionar las opciones disponibles
        available_options = "\n".join([f"{i+1}. {key.capitalize().replace('_', ' ')}" for i, key in enumerate(patterns.keys())])
        suggestion = (f"❓ I'm sorry, I didn't quite catch that. Here are some things I can help you with:\n\n"
                      f"{available_options}\n\n"
                      f"👉 *Example*: 'Please send opening hours from MyRestaurantName'\n\n"
                      f"Let me know how I can assist you! 😊")

    # Dividir el mensaje original para hacerlo más claro y amigable
    intro_message = f"Hi <@{user}>, I noticed your message: *'{text}'*."
    explanation_message = (
        "It seems I couldn't understand your request. "
        "But don't worry, here are some examples of what I can help you with:"
    )
    closing_message = (
        "Feel free to try again with one of the options above, or let me know if you need something else! 😊"
    )

    # Construir el mensaje completo con opciones de ayuda
    full_message = (f"{intro_message}\n\n{explanation_message}\n\n{suggestion}\n\n{closing_message}")

    # Enviar el mensaje al canal en el hilo correspondiente
    try:
        client.web_client.chat_postMessage(
            channel=channel,
            text=full_message,
            thread_ts=thread_ts
        )
    except SlackApiError as e:
        logging.error(f"Error sending unknown command response: {e.response['error']}")
