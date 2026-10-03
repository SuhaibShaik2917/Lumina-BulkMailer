# Lumina Dispatch | Professional Career Outreach System

Lumina Dispatch is a streamlined Python-based application designed for professional career outreach. It allows users to send personalized emails with resume attachments to multiple recipients efficiently.

## 🚀 Features
- **Standalone GUI**: No server setup required. Launch and send instantly.
- **Bulk Transmission**: Send to multiple target emails from a single list.
- **Resume Integration**: Easy PDF attachment for professional applications.
- **Credential Management**: Supports `config.json` for fast loading of authentication details.
- **Secure Connectivity**: Uses TLS encryption for secure communication with Gmail SMTP.

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.x installed on your system.

### Setup
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd LuminaDispatch
   ```
2. Create a `config.json` file in the root directory (or update the existing one):
   ```json
   {
       "auth_email": "your-email@gmail.com",
       "auth_pass": "your-app-password"
   }
   ```
   *Note: You must use a **Google App Password**, not your regular Gmail password.*

### Running the App
- **Windows**: Double-click `Run_Lumina_Mailer.bat`
- **Terminal**: Run `python simple_mailer.py`

## ⚠️ Security Notice
Never commit your `config.json` file to a public repository. Always use the provided `.gitignore` to keep your credentials private.
