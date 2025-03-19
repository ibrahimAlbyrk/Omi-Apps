# ✨ MailMate - Intelligent Email Management System ✉️
<p align="center">
  <a href="https://github.com/BasedHardware/omi"><img src="https://img.shields.io/badge/OMI%20Github-brightgreen.svg?style=for-the-badge&colorA=000000&colorB=ffffff"></a>
  <a href="https://docs.omi.me/docs/developer/apps/IntegrationActions"><img src="https://img.shields.io/badge/Integrations%20Actions%20Docs-brightgreen.svg?style=for-the-badge&colorA=000000&colorB=ffffff"></a>
</p>

## 🚀 Project Overview

MailMate is an AI-powered system that analyzes, classifies, and processes your emails. Integrated with the Gmail API, it detects important emails, performs sentiment analysis, and directs them to the Omi platform when necessary.

This project helps users **avoid missing important emails** and **save time by filtering out spam**, allowing for a more efficient communication process. 📩✨

---

## 🛠️ Technology Stack

| Technology | Description |
|------------|------------|
| **Python** 🐍 | Core development language |
| **Flask** 🌐 | Webhook and API management |
| **OpenAI API** 🤖 | AI-powered email classification |
| **Gmail API** 📬 | Fetching emails from Google accounts |
| **SQLite** 🗃️ | Database for user management |
| **Threading** 🔄 | Background email processing |
| **Logging System** 📜 | Advanced logging and error handling |

---

## 🔥 Key Features

✅ **Automated Email Classification**  
📌 **Detects important emails** (e.g., invoices, meetings, security alerts)  
🚨 **Assigns priority levels** (High, Medium, Low)  
📧 **Identifies emails that require a response**  

✅ **Omi Integration**  
✍️ **Summarizes emails and analyzes sentiment**  
🔗 **Suggests relevant actions (reply, schedule a meeting, make a payment, etc.)**  

✅ **Real-time Tracking & Notifications**  
🕵️ **Continuously monitors incoming emails**  
🔔 **Notifies users about important emails**  

---

## 📌 Installation Guide

### 1️⃣ Install Required Dependencies

```sh
pip install -r requirements.txt
```

### 2️⃣ Configure Environment Variables

Create a `.env` file and populate it as follows:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Omi API Key
OMI_API_KEY=your_omi_api_key
OMI_APP_ID=your_omi_app_id

# Google OAuth Configuration
GOOGLE_CLIENT_SECRET=path/to/google_client_secret.json
```

### 3️⃣ Start the Flask Server

```sh
python Main.py
```

---

## 📜 Code Architecture

```
📂 MailMate
├── 📜 Main.py                  # Main entry point of the application
├── 📜 Config.py                # API keys and configurations
├── 📜 Database.py              # SQLite database for user management
├── 📜 email_service.py         # Gmail API integration
├── 📜 classification_service.py # AI-powered email classification
├── 📜 action_service.py        # Omi API integration
├── 📜 new_emails_monitor.py    # Email tracking system
├── 📜 thread_manager.py        # Background process management
└── 📜 Logger.py                # Logging and error handling
```

### 🔹 **Main Components**

#### 📍 `classification_service.py` - **Email Classification**  
🔍 Uses OpenAI API to classify incoming emails based on **priority, content, and importance**.

#### 📍 `email_service.py` - **Email Management**  
📨 Fetches emails from the Gmail API, retrieves all/unread messages, and extracts content.

#### 📍 `action_service.py` - **Omi Integration**  
🛠️ Sends classified emails to the Omi system for further processing.

#### 📍 `thread_manager.py` - **Background Processing**  
⏳ Manages **multi-threaded** email scanning operations to keep the system running smoothly.

---

## 📌 API Usage

📍 **Login**  
`GET /login?uid=your_user_id`  

📍 **Logout**  
`POST /logout?uid=your_user_id`
