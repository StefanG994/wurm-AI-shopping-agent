from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Iterable, List, Literal, Optional, cast

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict, Field

from handlers.gpt_handlers.gpt_agents.base_agent import BaseAgent
from handlers.gpt_handlers.gpt_agents.communication_agent import CommunicationAgent
from handlers.multi_intent import ParsedIntent
from handlers.shopware_handlers.shopware_product_client import ProductClient
from handlers.shopware_handlers.shopware_utils import SimpleHeaderInfo


class ProductProperty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


class ProductQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="Canonical name for the requested product (e.g., 'earbuds')")
    brand: str | None = Field(default=None, description="Brand associated with the product request")
    properties: List[ProductProperty] = Field(default_factory=list)


class FilterParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str | int | float | bool | None = None


class SearchFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    field: str | None = None
    value: str | int | float | bool | None = None
    parameters: List[FilterParameter] | None = None


class IncludeDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str
    fields: List[str] = Field(default_factory=list)


class AssociationDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    includes: List[str] = Field(default_factory=list)
    limit: int | None = None


class SortRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    order: Literal["ASC", "DESC", "asc", "desc"] = "ASC"


class CriteriaPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int | None = None
    limit: int | None = None
    filter: List[SearchFilter] | None = None
    sort: List[SortRule] | None = None
    aggregations: List[str] | None = None


class SearchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    productNumber: str | None = None
    search: str | None = None
    order: str | None = None
    limit: int | None = None
    quantity: int | None = None
    page: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    manufacturer: str | None = None
    properties: str | None = None
    shipping_free: bool | None = None
    rating: int | None = None
    filter: List[SearchFilter] | None = None
    includes: List[IncludeDefinition] | None = None
    associations: List[AssociationDefinition] | None = None
    category_id: str | None = None
    criteria: CriteriaPayload | None = None
    productId: str | None = None
    options: List[str] | None = None
    switchedGroup: str | None = None
class SearchIntentExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    productNumber: str | None = None
    quantity: int | None = None
    action: Literal[
        "search_product_by_productNumber",
        "search_products_by_description",
        "list_products",
        "product_listing_by_category",
        "search_suggest",
        "get_product",
        "product_cross_selling",
        "find_variant",
    ]
    payload: SearchPayload = Field(
        default_factory=SearchPayload,
        description="Normalized parameters ready for the Shopware API call",
    )
    product_queries: List[ProductQuery] = Field(default_factory=list)
    intent_summary: str | None = Field(default=None, description="High-level summary of the customer's request")


class CommunicationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    missing: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ProductSearchResponse(SearchIntentExtraction):
    missing: List[str] = Field(default_factory=list)
    communication: CommunicationPlan | None = None
    shopware_response: Dict[str, Any] | None = None


class SearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(name=self.__class__.__name__)
        self.load_function_schemas("search_agent_function_schema.json")
        self.communication_agent = CommunicationAgent()
        self.product_client = ProductClient()

    def include_additional_parts_to_prompt(self, extra_sections: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if not extra_sections:
            return {}
        sections = [f"{title}:\n{content}" for title, content in extra_sections.items()]
        return {"role": "user", "content": "\n\n".join(sections)}

    async def plan_search(
        self,
        customer_message: str,
        *,
        language_id: Optional[str] = None,
        header_info: Optional[SimpleHeaderInfo] = None,
        parsed_intents: Optional[List[ParsedIntent]] = None,
    ) -> ProductSearchResponse:
        intent_hints: List[Dict[str, Any]] = []
        if parsed_intents:
            intent_hints = [intent.model_dump() for intent in parsed_intents]

        msgs = self.build_messages_with_system(
            "SEARCH_AGENT",
            customer_message,
            language_id=language_id,
            variables={"SEARCH_TOOLS": self.tools},
            extra_sections={"PARSED_INTENTS": json.dumps(intent_hints, ensure_ascii=False)} if intent_hints else None,
        )
        resp = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model=self.get_small_llm_model(),
            messages=cast("Iterable[ChatCompletionMessageParam]", msgs),
            response_format=SearchIntentExtraction,
        )

        extraction = resp.choices[0].message.parsed
        if extraction is None:
            raise RuntimeError("Failed to parse search product response: parsed value is None")
        
        search_response = ProductSearchResponse(**extraction.model_dump())
        self._merge_with_intent_hints(search_response, parsed_intents)
        payload = self._normalize_payload(search_response)
        # _normalize_payload already sets search_response.payload to a SearchPayload instance.
        # Avoid assigning a raw dict to the typed payload attribute to satisfy static type checking.
        # keep the dict 'payload' for further processing.
        
        missing = self._missing_required_fields(search_response.action, payload)
        search_response.missing = missing

        if missing:
            search_response.communication = await self._ask_for_missing_params(
                action=search_response.action,
                missing=missing,
                payload=payload,
                customer_message=customer_message,
                language_id=language_id,
            )
            return search_response

        shopware_result = await self._execute_shopware_action(
            action=search_response.action,
            payload=payload,
            header_info=header_info,
            language_id=language_id,
        )
        search_response.shopware_response = shopware_result
        return search_response

    def _merge_with_intent_hints(
        self,
        search_response: ProductSearchResponse,
        parsed_intents: Optional[List[ParsedIntent]],
    ) -> None:
        if not parsed_intents:
            return
        payload_data = self._payload_to_dict(search_response.payload)
        for intent in parsed_intents:
            if intent.function == search_response.action and intent.parameters:
                param_dict = (
                    intent.parameters.model_dump(exclude_none=True)
                    if hasattr(intent.parameters, "model_dump")
                    else dict(intent.parameters)
                )
                for key, value in param_dict.items():
                    payload_data.setdefault(key, value)
                if not search_response.description and isinstance(param_dict.get("search"), str):
                    search_response.description = param_dict.get("search")
                if not search_response.intent_summary and intent.summary:
                    search_response.intent_summary = intent.summary
                break
        search_response.payload = self._dict_to_payload(payload_data)

    def _payload_to_dict(self, payload: SearchPayload | None) -> Dict[str, Any]:
        if payload is None:
            return {}
        data = payload.model_dump(exclude_none=True)

        def _convert_filters(filters: List[dict]) -> List[dict]:
            converted: List[dict] = []
            for filt in filters:
                filt = dict(filt)
                parameters = filt.get("parameters")
                if parameters is not None:
                    filt["parameters"] = {param["key"]: param.get("value") for param in parameters}
                converted.append(filt)
            return converted

        if includes := data.get("includes"):
            data["includes"] = {inc["alias"]: inc.get("fields", []) for inc in includes}

        if associations := data.get("associations"):
            assoc_dict: Dict[str, Any] = {}
            for assoc in associations:
                payload_assoc = {"includes": assoc.get("includes", [])}
                if assoc.get("limit") is not None:
                    payload_assoc["limit"] = assoc["limit"]
                assoc_dict[assoc["name"]] = payload_assoc
            data["associations"] = assoc_dict

        if filters := data.get("filter"):
            data["filter"] = _convert_filters(filters)

        if criteria := data.get("criteria"):
            crit = dict(criteria)
            if crit_filters := crit.get("filter"):
                crit["filter"] = _convert_filters(crit_filters)
            if crit_sort := crit.get("sort"):
                crit["sort"] = [dict(item) for item in crit_sort]
            data["criteria"] = crit

        return data

    def _dict_to_payload(self, payload: Dict[str, Any]) -> SearchPayload:
        data = dict(payload)

        if includes := data.get("includes"):
            if isinstance(includes, dict):
                data["includes"] = [{"alias": alias, "fields": fields or []} for alias, fields in includes.items()]

        if associations := data.get("associations"):
            assoc_list: List[dict] = []
            if isinstance(associations, dict):
                for name, value in associations.items():
                    assoc_entry = {"name": name}
                    if isinstance(value, dict):
                        assoc_entry["includes"] = value.get("includes", [])
                        if value.get("limit") is not None:
                            assoc_entry["limit"] = value["limit"]
                    assoc_list.append(assoc_entry)
            data["associations"] = assoc_list

        def _convert_filters_back(filters: Any) -> Any:
            if not isinstance(filters, list):
                return filters
            converted: List[dict] = []
            for filt in filters:
                filt = dict(filt)
                parameters = filt.get("parameters")
                if isinstance(parameters, dict):
                    filt["parameters"] = [{"key": k, "value": v} for k, v in parameters.items()]
                converted.append(filt)
            return converted

        if filters := data.get("filter"):
            data["filter"] = _convert_filters_back(filters)

        if criteria := data.get("criteria"):
            crit = dict(criteria)
            if crit_filters := crit.get("filter"):
                crit["filter"] = _convert_filters_back(crit_filters)
            if crit_sort := crit.get("sort"):
                crit["sort"] = [dict(item) for item in crit_sort]
            data["criteria"] = crit

        return SearchPayload(**data)

    def _normalize_payload(self, response: ProductSearchResponse) -> Dict[str, Any]:
        payload = self._payload_to_dict(response.payload)
        if response.action == "search_product_by_productNumber":
            if response.productNumber:
                payload.setdefault("productNumber", response.productNumber)
        if response.action == "search_products_by_description":
            description = response.description or ""
            if description:
                payload.setdefault("search", description)
        if response.quantity is not None:
            payload.setdefault("quantity", response.quantity)
        response.payload = self._dict_to_payload(payload)
        return payload

    def _missing_required_fields(self, action: str, payload: Dict[str, Any]) -> List[str]:
        schema = self.get_action_schema(action)
        required_fields = schema.get("parameters", {}).get("required", []) if schema else []
        missing: List[str] = []
        for field in required_fields:
            value = payload.get(field)
            if value in (None, "", []):
                missing.append(field)
        return missing

    async def _ask_for_missing_params(
        self,
        *,
        action: str,
        missing: List[str],
        payload: Dict[str, Any],
        customer_message: str,
        language_id: Optional[str],
    ) -> CommunicationPlan:
        seed = {
            "missing": missing,
            "action": action,
            "knownPayload": payload,
        }
        plan = await self.communication_agent.plan_communication(
            seed=seed,
            customerMessage=customer_message,
            language_id=language_id,
        )
        message = ""
        ctx: Dict[str, Any] = {}
        steps = plan.get("steps") if isinstance(plan, dict) else None
        if isinstance(steps, list) and steps:
            parameters = steps[0].get("parameters", {})
            if isinstance(parameters, dict):
                message = parameters.get("message") or ""
                ctx = parameters.get("context") or {}
                reported_missing = parameters.get("missing")
                if isinstance(reported_missing, list) and reported_missing:
                    missing = [str(m) for m in reported_missing]

        return CommunicationPlan(
            message=message or "Could you provide the missing information?",
            missing=missing,
            context=ctx,
            raw=plan if isinstance(plan, dict) else {},
        )

    async def _execute_shopware_action(
        self,
        *,
        action: str,
        payload: Dict[str, Any],
        header_info: Optional[SimpleHeaderInfo],
        language_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if header_info is None:
            self.logger.warning("Header info missing; skipping Shopware call for action %s", action)
            return None

        try:
            lang = language_id or header_info.languageId or ""
            context_token = getattr(header_info, "contextToken", None)
            sales_channel = getattr(header_info, "salesChannelId", None)

            if action == "search_products_by_description":
                return await self.product_client.search_products(
                    body=payload,
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )
            if action == "search_product_by_productNumber":
                product_number = payload.get("productNumber")
                if not product_number:
                    raise ValueError("productNumber is required for search_product_by_productNumber")
                lang_override = lang or header_info.languageId or ""
                res = await self.product_client.get_product_by_productNumber(product_number, language_id=lang_override or "en-GB")
                # Normalize result to match return type Optional[Dict[str, Any]]
                if res is None:
                    return None
                if isinstance(res, dict):
                    return res
                return {"product": res}
            if action == "list_products":
                return await self.product_client.list_products(body=payload)
            if action == "product_listing_by_category":
                category_id = payload.get("category_id")
                if not isinstance(category_id, str) or not category_id:
                    raise ValueError("category_id is required for product_listing_by_category")
                body = {k: v for k, v in payload.items() if k != "category_id"}
                return await self.product_client.product_listing_by_category(
                    category_id,
                    body=body,
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )
            if action == "search_suggest":
                return await self.product_client.search_suggest(
                    body=payload,
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )
            if action == "get_product":
                product_id = payload.get("productId")
                if not product_id:
                    raise ValueError("productId is required for get_product")
                return await self.product_client.get_product(
                    productId=product_id,
                    body={k: v for k, v in payload.items() if k != "productId"},
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )
            if action == "product_cross_selling":
                product_id = payload.get("productId")
                if not product_id:
                    raise ValueError("productId is required for product_cross_selling")
                body = {k: v for k, v in payload.items() if k != "productId"}
                return await self.product_client.product_cross_selling(
                    productId=product_id,
                    body=body,
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )
            if action == "find_variant":
                product_id = payload.get("productId")
                options = payload.get("options")
                if not product_id or not options:
                    raise ValueError("productId and options are required for find_variant")
                switched_group = payload.get("switchedGroup")
                return await self.product_client.find_variant(
                    productId=product_id,
                    options=options,
                    switched_group=switched_group,
                    context_token=context_token,
                    language_id=lang,
                    sales_channel_id=sales_channel,
                )

            self.logger.warning("No Shopware mapping implemented for action %s", action)
            return None
        except Exception as exc:
            self.logger.exception("Failed to execute Shopware action %s", action)
            return {"error": str(exc)}
