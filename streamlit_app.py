import streamlit as st
from groq import Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])  #
from config import get_api_key, get_model, DEFAULT_MODEL
from utils.file_reader import (
    read_inventory,
    read_shipping,
    read_contract,
    read_suppliers,
    generate_sample_inventory,
    generate_sample_shipping,
    generate_sample_suppliers,
)
from utils.analyzer import (
    analyze_inventory,
    analyze_shipping,
    build_data_summary,
    find_column,
)
from utils.visualizations import (
    inventory_quantity_chart,
    shipping_status_chart,
    shipping_delay_chart,
    alternate_suppliers_chart,
)
from utils.ai_engine import (
    ask_question,
    summarize_contract,
    recommend_disruption_response,
    summarize_web_leads,
    AIEngineError,
)
from utils.disruption_advisor import (
    days_until_stockout,
    find_alternate_suppliers,
    build_disruption_context,
)
from utils.web_search import search_alternative_suppliers, WebSearchError

st.set_page_config(
    page_title="AI Supply Chain Control Center",
    page_icon="📦",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
for key in ("inventory_df", "shipping_df", "contract_text", "suppliers_df", "chat_history"):
    if key not in st.session_state:
        st.session_state[key] = [] if key == "chat_history" else None

# ---------------------------------------------------------------------------
# Sidebar: AI configuration + sample data
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        help=(
            "Leave blank to use the GROQ_API_KEY environment variable "
            "or Streamlit secrets, if configured. Get a free key at "
            "https://console.groq.com/keys"
        ),
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input

    st.session_state["model"] = st.text_input(
        "Model", value=st.session_state.get("model") or DEFAULT_MODEL
    )

    st.divider()
    st.subheader("📄 No data handy?")
    st.caption("Download sample files to try the app out.")
    st.download_button(
        "Sample inventory.xlsx",
        data=generate_sample_inventory(),
        file_name="sample_inventory.xlsx",
    )
    st.download_button(
        "Sample shipping.csv",
        data=generate_sample_shipping(),
        file_name="sample_shipping.csv",
    )
    st.download_button(
        "Sample suppliers.csv",
        data=generate_sample_suppliers(),
        file_name="sample_suppliers.csv",
    )

st.title("📦 AI Supply Chain Control Center")
st.write("Upload your inventory, shipping, and contract data, then ask questions in plain English.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_inventory, tab_shipping, tab_contract, tab_dashboard, tab_disruption, tab_ai = st.tabs(
    ["📦 Inventory", "🚚 Shipping", "📄 Contract", "📊 Dashboard", "🚨 Disruption Advisor", "🤖 Ask AI"]
)

# --- Inventory tab ----------------------------------------------------------
with tab_inventory:
    inventory_file = st.file_uploader("Upload Inventory Excel", type=["xlsx"])
    if inventory_file:
        try:
            st.session_state["inventory_df"] = read_inventory(inventory_file)
        except ValueError as exc:
            st.error(str(exc))

    df = st.session_state["inventory_df"]
    if df is not None:
        st.dataframe(df, use_container_width=True)

        result = analyze_inventory(df)
        for w in result["warnings"]:
            st.warning(w)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total units", result["total_items"] if result["total_items"] is not None else "—")
        col2.metric(
            "Inventory value",
            f"${result['total_value']:,.2f}" if result["total_value"] is not None else "—",
        )
        col3.metric("Low stock items", len(result["low_stock"]))

        if not result["low_stock"].empty:
            st.subheader("⚠️ Low Stock Alerts")
            st.dataframe(result["low_stock"], use_container_width=True)

        if not result["overstock"].empty:
            st.subheader("📦 Overstock")
            st.dataframe(result["overstock"], use_container_width=True)
    else:
        st.info("Upload an inventory Excel file to see analysis here.")

# --- Shipping tab ------------------------------------------------------------
with tab_shipping:
    shipping_file = st.file_uploader("Upload Shipping CSV", type=["csv"])
    if shipping_file:
        try:
            st.session_state["shipping_df"] = read_shipping(shipping_file)
        except ValueError as exc:
            st.error(str(exc))

    df = st.session_state["shipping_df"]
    if df is not None:
        st.dataframe(df, use_container_width=True)

        result = analyze_shipping(df)
        for w in result["warnings"]:
            st.warning(w)

        col1, col2 = st.columns(2)
        col1.metric(
            "On-time rate",
            f"{result['on_time_rate']}%" if result["on_time_rate"] is not None else "—",
        )
        col2.metric(
            "Avg delay (days)",
            result["avg_delay_days"] if result["avg_delay_days"] is not None else "—",
        )

        if not result["delayed"].empty:
            st.subheader("⚠️ Delayed Shipments")
            st.dataframe(result["delayed"], use_container_width=True)
    else:
        st.info("Upload a shipping CSV file to see analysis here.")

# --- Contract tab --------------------------------------------------------------
with tab_contract:
    contract_file = st.file_uploader("Upload Vendor Contract PDF", type=["pdf"])
    if contract_file:
        try:
            st.session_state["contract_text"] = read_contract(contract_file)
        except ValueError as exc:
            st.error(str(exc))

    text = st.session_state["contract_text"]
    if text:
        if st.button("✨ Summarize with AI"):
            try:
                with st.spinner("Reading the contract..."):
                    summary = summarize_contract(
                        text, api_key=get_api_key(), model=get_model()
                    )
                st.markdown(summary)
            except AIEngineError as exc:
                st.error(str(exc))

        with st.expander("View full extracted text"):
            st.text(text)
    else:
        st.info("Upload a vendor contract PDF to see it here.")

# --- Dashboard tab ---------------------------------------------------------
with tab_dashboard:
    inv_df = st.session_state["inventory_df"]
    ship_df = st.session_state["shipping_df"]

    if inv_df is None and ship_df is None:
        st.info("Upload inventory and/or shipping data to see charts here.")
    else:
        if inv_df is not None:
            fig = inventory_quantity_chart(inv_df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        if ship_df is not None:
            col1, col2 = st.columns(2)
            fig1 = shipping_status_chart(ship_df)
            fig2 = shipping_delay_chart(ship_df)
            if fig1:
                col1.plotly_chart(fig1, use_container_width=True)
            if fig2:
                col2.plotly_chart(fig2, use_container_width=True)

# --- Disruption Advisor tab -------------------------------------------------
with tab_disruption:
    st.write(
        "Model a supply disruption — a supplier outage, a natural disaster, "
        "a blocked shipping route — and get a decisive response plan in seconds."
    )

    suppliers_file = st.file_uploader(
        "Upload Supplier Directory CSV", type=["csv"], key="suppliers_uploader"
    )
    if suppliers_file:
        try:
            st.session_state["suppliers_df"] = read_suppliers(suppliers_file)
        except ValueError as exc:
            st.error(str(exc))

    suppliers_df = st.session_state["suppliers_df"]
    if suppliers_df is not None:
        with st.expander("View supplier directory"):
            st.dataframe(suppliers_df, use_container_width=True)
    else:
        st.info(
            "Upload a supplier directory CSV (or download the sample in the "
            "sidebar) so the advisor has alternatives to search."
        )

    st.divider()

    inv_df = st.session_state["inventory_df"]
    name_col = find_column(inv_df, ["item", "product", "name"]) if inv_df is not None else None
    qty_col = find_column(inv_df, ["quantity", "qty", "stock"]) if inv_df is not None else None

    col_a, col_b = st.columns(2)

    with col_a:
        if inv_df is not None and name_col:
            item_options = inv_df[name_col].dropna().astype(str).tolist()
            item_name = st.selectbox("Affected item", item_options) if item_options else ""
        else:
            item_name = st.text_input("Affected item")

        default_qty = 0.0
        if inv_df is not None and name_col and qty_col and item_name:
            row = inv_df[inv_df[name_col].astype(str) == str(item_name)]
            if not row.empty:
                try:
                    default_qty = float(row.iloc[0][qty_col])
                except (TypeError, ValueError):
                    default_qty = 0.0

        current_quantity = st.number_input(
            "Current quantity on hand", min_value=0.0, value=default_qty
        )
        daily_usage_rate = st.number_input(
            "Estimated daily usage", min_value=0.0, value=5.0, step=1.0
        )

    with col_b:
        disrupted_supplier = st.text_input("Disrupted supplier (optional)")
        affected_region = st.text_input(
            "Region affected (optional)",
            placeholder="e.g. Chennai, Tamil Nadu",
        )
        disruption_reason = st.text_area(
            "What happened?",
            placeholder="e.g. Flood has cut off deliveries from this region for a month",
            height=100,
        )

    if st.button("🚨 Generate Response Plan", type="primary"):
        if not item_name:
            st.warning("Enter or select an affected item first.")
        elif suppliers_df is None:
            st.warning("Upload a supplier directory (or use the sample in the sidebar) first.")
        else:
            days_left = days_until_stockout(current_quantity, daily_usage_rate)
            alternatives = find_alternate_suppliers(
                suppliers_df, item_name, exclude_supplier=disrupted_supplier
            )

            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Days until stockout",
                days_left if days_left is not None else "—",
            )
            col2.metric("Alternatives found", len(alternatives))
            supplier_col = (
                find_column(alternatives, ["supplier", "vendor"])
                if not alternatives.empty
                else None
            )
            col3.metric(
                "Fastest alternative",
                alternatives.iloc[0][supplier_col]
                if supplier_col and not alternatives.empty
                else "—",
            )

            if not alternatives.empty:
                st.dataframe(alternatives, width='stretch')
                fig = alternate_suppliers_chart(alternatives)
                if fig:
                    st.plotly_chart(fig, width='stretch')
                web_leads = None
            else:
                st.warning("No alternative supplier found in your directory for this item.")
                web_leads = None
                try:
                    with st.spinner("🌐 No backup on file — searching the web..."):
                        search_results = search_alternative_suppliers(
                            item_name,
                            avoid_terms=[disrupted_supplier, affected_region],
                        )
                        web_leads = summarize_web_leads(
                            item_name,
                            search_results,
                            api_key=get_api_key(),
                            model=get_model(),
                        )
                except WebSearchError as exc:
                    st.info(str(exc))
                except AIEngineError as exc:
                    st.error(str(exc))

                if web_leads:
                    st.subheader("🌐 Web-sourced leads (verify before ordering)")
                    st.caption(
                        "Found via live web search — these are real "
                        "company names and links, not a verified vendor "
                        "list. Click through and contact them directly."
                    )
                    st.markdown(web_leads)
                    with st.expander("Raw search results"):
                        for r in search_results:
                            st.markdown(
                                f"- [{r.get('title', '')}]({r.get('href', '')}) "
                                f"— {r.get('body', '')}"
                            )

            context = build_disruption_context(
                item_name=item_name,
                current_quantity=current_quantity,
                daily_usage_rate=daily_usage_rate,
                days_left=days_left,
                disrupted_supplier=disrupted_supplier,
                disruption_reason=disruption_reason,
                alternatives_df=alternatives,
                affected_region=affected_region,
                web_leads=web_leads,
            )

# --- Ask AI tab --------------------------------------------------------------
with tab_ai:
    st.write("Ask a question about whatever data you've loaded so far.")

    for role, message in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.markdown(message)

    question = st.chat_input("e.g. Which items should I reorder this week?")
    if question:
        st.session_state["chat_history"].append(("user", question))
        with st.chat_message("user"):
            st.markdown(question)

        context = build_data_summary(
            inventory_df=st.session_state["inventory_df"],
            shipping_df=st.session_state["shipping_df"],
            contract_text=st.session_state["contract_text"],
        )

        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking..."):
                    answer = ask_question(
                        question,
                        context,
                        api_key=get_api_key(),
                        model=get_model(),
                    )
                st.markdown(answer)
                st.session_state["chat_history"].append(("assistant", answer))
            except AIEngineError as exc:
                st.error(str(exc))