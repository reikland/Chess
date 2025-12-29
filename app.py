import streamlit as st

from services.registry import ServiceRegistry
from ui.state import init_session_state


def build_services() -> ServiceRegistry:
    """Create the service registry with default entries.

    Replace or extend this function when real services are available.
    """
    registry = ServiceRegistry()
    registry.register("placeholder_engine", "Not yet implemented")
    return registry


def main() -> None:
    st.set_page_config(page_title="Chess", layout="wide")

    services = build_services()
    init_session_state()

    st.title("Chess Application")
    st.write("Base layout ready for engine, UI, and services wiring.")

    st.subheader("Services")
    if services.names():
        st.write({name: str(service) for name, service in services.items()})
    else:
        st.write("No services registered yet.")

    st.subheader("Session State")
    st.json({
        "game": st.session_state.get("game"),
        "preferences": st.session_state.get("preferences"),
    })


if __name__ == "__main__":
    main()
