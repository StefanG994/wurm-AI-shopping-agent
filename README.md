# wurm-AI-shopping-agent
Project for Wurm. AI shopping multi-agent system with bi-temporal knowledge graph as long-term memory.
Graphiti:
1. GitHub: https://github.com/getzep/graphiti
2. Getting started: https://help.getzep.com/graphiti/getting-started/quick-start


How to run the project:
1. Create virtual environment, open terminal and paste in the following command
python -m venv venv

2. After that, to activate the virtual environment, type in:  
On Windows:         venv\Scripts\activate or venv\Scripts\activate.bat  
On Linux/Mac:        source venv/bin/activate  
  
3. The virtual environment is activated and it is safe to install libraries in it locally. The list of needed libraries is in requirements.txt file. Type in the following commands: 
3.a Upgrade pip: python -m pip install --upgrade pip wheel  
3.b Install requirements: pip install -r requirements.txt
  
4. To start up the application locally, type in the following command using uvicorn:  
uvicorn main:app --reload --host 0.0.0.0 --port 8000
