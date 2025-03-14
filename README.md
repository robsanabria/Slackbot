# 🤖 Tier 2 Slack Bot - Asistente Operativo Inteligente

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0-000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-5.0-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT-412991?logo=openai&logoColor=white)](https://openai.com/)

Bot de Slack inteligente que automatiza procesos operativos mediante NLP y gestión de datos en tiempo real, mejorando la productividad del equipo.

## 🌟 Características Principales

### 🤖 Automatización Inteligente
- **Procesamiento de solicitudes**: Respuesta a menciones (`@bot`) en tiempo real
- **Integración con OpenAI**:
  - ✅ Generación de respuestas contextuales con GPT
  - ✅ Análisis semántico avanzado
- **Envío automatizado**: Mensajes programados a canales específicos

### 🗃️ Gestión de Datos
- **Conexión con MongoDB**:
  - 📅 Horarios operativos
  - 📞 Información de contacto
  - ⚙️ Configuraciones de entrega
- **Actualizaciones dinámicas**: Sincronización en tiempo real

### 🛠️ Arquitectura
- **Diseño modular**:
  - 🧩 Servicios independientes (Slack, OpenAI, MongoDB)
  - 🔐 Gestión segura de credenciales
- **Pruebas**:
  - 🧪 Unitarias con pytest (cobertura > 75%)
  - 🚦 Integración continua (GitHub Actions)

## 🛠️ Tecnologías Utilizadas


| Categoría         | Tecnologías                                      |
|-------------------|-------------------------------------------------|
| **Backend**       | Python 3.9, Flask, Slack SDK                    |
| **Base de Datos** | MongoDB Atlas, PyMongo                          |
| **IA**            | OpenAI API, Prompt Engineering                 |
| **Herramientas**  | Postman, Ngrok, Python-dotenv                  |

## ⚙️ Configuración

1. **Requisitos**:
```bash
Python 3.9+
MongoDB Atlas Cluster
Slack Workspace con permisos de bot
