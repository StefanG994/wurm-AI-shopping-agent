from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import logging

from handlers.prompts_translated.get_translated_prompt import get_translated_prompt
from handlers.shopware_handlers.shopware_utils import SimpleHeaderInfo

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
	
	def load_function_schemas(self, schema_name: str):
		base_dir = os.path.dirname(__file__)
		schema_path = os.path.join(base_dir, schema_dir, schema_name)
		with open(schema_path, "r", encoding="utf-8") as f:
			self.tools = json.load(f)
			self.logger.info("[TEST]FUNCTION SCHEMA %s", self.tools)
		
	def get_action_schema(self, action_name: str) -> Dict[str, Any]:
		if self.tools is None:
			return {}
		
		for item in self.tools:
			if item.get('name') == action_name:
				return item

	def get_function_parameter_info(self, function_name: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
		function_schema = self.get_action_schema(function_name)
		if not function_schema:
			raise RuntimeError(f"Error: Function '{function_name}' not found")

		param_properties = function_schema.get("parameters", {}).get("properties", {})
		required_params = function_schema.get("parameters", {}).get("required", [])
		self.logger.info(f"[TEST] REQUIRED PARAMS: {required_params}")
		payload: Dict[str, Any] = {}

		def put(k: str, v: Any) -> None:
			if v is not None:
				payload[k] = v
				
		for param_name, param_info in param_properties.items():
			self.logger.info(f"[TEST] PARAM NAME: {param_name}, PARAM_INFO: {param_info}")
			if param_value := params.get(param_name) and param_name in required_params:
				required_params.remove(param_name)
			put(param_name, params.get(param_name))

		self.logger.info(f"[TEST] PAYLOAD: {payload}")
		return payload, required_params
	
	def build_messages_with_system(self, system_key: str,
				customerMessage: str,
				# last_result: Optional[Dict[str, Any]],
				# history: Optional[List[Dict[str, Any]]],
				*,
				language_id: Optional[str] = None,
				variables: Optional[Dict[str, Any]] = None,
				extra_sections: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:

		# outline = make_outline_via_gpt(customerMessage, history or [], last_result or {}, language_id=language_id)
		system_prompt = get_translated_prompt(system_key, language_id=language_id, variables=variables or {})

		msgs: List[Dict[str, str]] = [
			{"role": "system", "content": "In the output JSON, 'steps' cannot be an empty array"},
			{"role": "system", "content": system_prompt.strip()},
			{"role": "user", "content": f"USER GOAL:\n{customerMessage}".strip()},
			# {"role": "user", "content": "CONTEXT_OUTLINE:\n" + outline},
		]

		if extra_prompt := self.include_additional_parts_to_prompt(extra_sections):
			msgs.append(extra_prompt)

		msgs.append({"role": "user", "content": "Return STRICT JSON with keys: mode, steps, done, response_text."})
		
		return msgs
	
	def include_additional_parts_to_prompt(self, extra_sections: Optional[Dict[str, str]] = None) -> Dict[str, str]:
		return None

	
