from __future__ import annotations
import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import logging

try:
	from openai import OpenAI
except ImportError:
	OpenAI = None

schema_dir = "agent_function_schemas"

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_LARGE = os.getenv("OPENAI_MODEL_LARGE", "")
OPENAI_MODEL_SMALL = os.getenv("OPENAI_MODEL_SMALL", "")

class BaseAgent:
	def __init__(self, name: str = "BaseAgent"):
		self.name = name
		self.logger = logging.getLogger(name)
		self.client = self._create_client()

	def _create_client(self):
		if OpenAI is None:
			raise RuntimeError("Install openai>=1.0.0 to use the new SDK (pip install openai)")
		return OpenAI(api_key=OPENAI_API_KEY)
	
	def get_client(self):
		return self.client
	
	def get_small_llm_model(self):
		return OPENAI_MODEL_SMALL
	
	def load_function_schemas(schema_name: str) -> List[Dict[str, Any]]:
		base_dir = os.path.dirname(__file__)
		schema_path = os.path.join(base_dir, schema_dir, schema_name)
		with open(schema_path, "r", encoding="utf-8") as f:
			return json.load(f)