import logging
from funciones import process_slack_message

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Lista de mensajes de prueba
test_messages = [
    "Hello @Sassito Slack Bot, can you create a test order ticket for Restaurant Example?",
    "Hey @Sassito Slack Bot, create a close restaurant ticket for My Restaurant.",
    "Can you create an open insights ticket for Some Restaurant?",
    "Please create a clarity check ticket for Another Restaurant.",
    "I need a delivery range ticket for Test Restaurant.",
    "Just a regular message without any specific pattern."
]

# Probar cada mensaje y mostrar la respuesta
for message in test_messages:
    print(f"Message: {message}")
    response = process_slack_message(message)
    print(f"Response: {response}")
    print("-" * 50)
