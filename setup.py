"""
Setup script for DealLens Strategy Agent
"""

import os
import subprocess
import sys

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists(".env"):
        print("Creating .env file...")
        env_content = """# Azure OpenAI Configuration
AOAI_API_KEY=your_azure_openai_api_key_here
AOAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AOAI_DEPLOY_GPT4O=gpt-4o
AOAI_API_VERSION=2024-10-21

# OpenAI Configuration (Alternative)
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
APP_NAME=DealLens Strategy Agent
DEBUG=True
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        print("✅ .env file created! Please update it with your API keys.")
    else:
        print("✅ .env file already exists.")

def main():
    """Main setup function"""
    print("🚀 Setting up DealLens Strategy Agent...")
    
    # Install requirements
    if not install_requirements():
        return
    
    # Create .env file
    create_env_file()
    
    print("\n🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Update the .env file with your API keys")
    print("2. Run: streamlit run main.py")
    print("3. Open your browser to the provided URL")

if __name__ == "__main__":
    main()
