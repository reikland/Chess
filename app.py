import streamlit as st

from services.registry import ServiceRegistry
from ui.layout import render_app


def build_services() -> ServiceRegistry:
    """Create the service registry with default entries.

    Replace or extend this function when real services are available.
    """
    registry = ServiceRegistry()
    registry.register("placeholder_engine", "Not yet implemented")
    return registry


def main() -> None:
    st.set_page_config(page_title="Chess", layout="wide")

    build_services()
    render_app()


if __name__ == "__main__":
    main()
