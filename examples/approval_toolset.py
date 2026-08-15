"""Example only: use PydanticAI native approval instead of a custom human-gate runtime."""

from pydantic_ai import FunctionToolset

from zuaef_agent.effects import EffectClass, requires_approval

product_tools = FunctionToolset()


@product_tools.tool_plain
def inspect_catalog(query: str) -> str:
    """Read-only lookup; no approval by default."""
    return f"catalog results for {query}"


@product_tools.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
def publish_product(product_id: int) -> str:
    """External side effect; PydanticAI pauses for native approval."""
    return f"published {product_id}"
