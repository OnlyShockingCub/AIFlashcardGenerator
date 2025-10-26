# Flashcards Generator with Python, Flask, and OpenAI API

This project is a Python-based flashcard generator that allows users to create flashcards on any topic they wish to learn about. The app uses Flask for the web server and OpenAI's API to generate the flashcards dynamically.

---

### **Important Notes**

- **OpenAI API Key**  
  You **must** provide your own OpenAI API key for the AI to function. The flashcards are powered by OpenAI's GPT model, which requires an active API key. You can obtain one by signing up at [OpenAI's platform](https://platform.openai.com/).

- **Flask Web Server**  
  The program uses Flask to run a local web server, which can be accessed through a user-friendly interface to generate your flashcards. You can easily run this app locally or deploy it to a cloud service for wider access.

---

### **Features**

- **Generate Flashcards:**  
  Create flashcards on any topic by simply entering a prompt. The AI generates questions and answers on the selected topic in real-time.

- **User-Friendly Web Interface:**  
  Powered by Flask, the app provides a simple web interface where you can input a topic and view the generated flashcards.

- **Customizable:**  
  You can adjust the number of flashcards and customize the difficulty of questions through the interface.

---

### **Requirements**

- Python 3.x
- Flask
- OpenAI Python Client

---

### **Installation**

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/flashcards-generator.git
   cd flashcards-generator
