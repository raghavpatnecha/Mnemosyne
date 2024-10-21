<div align="center">

<p align="center"> <img src="assets/mnemosyne_mini.png" width="1500px"></p>

</div>

[![](https://img.shields.io/github/license/sourcerer-io/hall-of-fame.svg?colorB=ff0000)](https://github.com/raghavpatnecha/Mnemosyne/blob/main/LICENSE)  [![](https://img.shields.io/badge/Raghav-Patnecha-brightgreen.svg?colorB=00ff00)](https://github.com/raghavpatnecha) [![](https://img.shields.io/badge/Akshay-Bahadur-brightgreen.svg?colorB=00ff00)](https://akshaybahadur.com)

# Mnemosyne
Mnemosyne is an intelligent conversational search agent for Medium articles, named after the Greek goddess of memory.

## Description 🛰️

Mnemosyne leverages Generative AI and other machine learning techniques to provide an intuitive, conversation-based interface for searching and exploring articles. Whether you're looking for specific information or wanting to dive deep into a topic, Mnemosyne acts as your personal search engine, offering relevant content and insights from a vast repository of your articles.

## Features 👨‍🔬

- Semantic Search through saved Medium Articles
- OpenAI and Ollama integration for QnA
- Firecrawl integration for crawling articles
- MongoDB integration for building vector and text data store

## Getting Started 🦄

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/mnemosyne.git
    cd mnemosyne
    ```

2. Install dependencies:  
   You can install Conda for Python to resolve machine learning dependencies.
    ```bash
    pip install -r requirements.txt
    ```

---

### Configuration

The main configuration for the project is done in the `src/config.py` file. Here's how you can configure it:

- **MongoDB Settings**:  
  Set up your MongoDB connection string and database name.
  
- **OpenAI/Ollama Settings**:  
  Provide your API keys for OpenAI and change the paramenters below based on your needs:
    ```
    class OPENAI:
        API_KEY: str = ""

    class LLM:
        MODEL_NAME: str = "gpt-4o-mini" #mistral,llama3.2
        TOKEN_LIMIT: int = 125000
        TEMPERATURE: float = 0.1
        OPENAI_TIMEOUT: int = 20 ```
  
- **Firecrawl Settings**:  
  Configure how often the system should crawl Medium for new articles.

---

### Usage

#### Running the Application

You can run the application in **Safe Mode** or **Unsafe Mode** . Safe Mode ensures strict, reliable operations, while Unsafe Mode offers faster processing but with some risks.


       python src/api/search.py
 

#### Code Overview
   - **config.py**: Configuration file containing settings for MongoDB, API keys, and other integrations.
   - **search.py**: Contains the code for starting Flask server.
   - **LLMService.py**: Provides the QnA service, contains code for text stream generation.
   - **MnemsoyneService.py**: Manages the overall Mnemosyne service, coordinating between search.py and llmservice.py.


## License 🚔

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contact 📱

For any queries or suggestions, please open an issue on this GitHub repository or contact the maintainers directly.

## Cite Us :pushpin:

```
@article{raghavpatnecha_mnemosyne,
author = [{Patnecha, Raghav}, {Bahadur, Akshay}],
journal = {https://github.com/raghavpatnecha/Mnemosyne},
month = {10},
title = {{Mnemosyne}},
year = {2024}
}
```

###### Made with ❤️ and 🦙 by Akshay Bahadur and Raghav Patnecha
---
