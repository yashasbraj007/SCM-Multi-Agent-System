import streamlit as st
import requests

st.title("Disruption Recovery Dashboard")
st.caption("Multi-agent supply chain disruption system")

if st.button("Load Open Disruptions"):
    resp = requests.get("http://localhost:5000/disruptions")
    st.dataframe(resp.json())

st.divider()

if st.button("Process Next Batch of Disruptions"):
    with st.spinner("Processing disruptions — this can take a few minutes while the LLM generates explanations..."):
        response = requests.post("http://localhost:5000/disruptions/process", timeout=600)
        results = response.json()

    for item in results:
        color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(item["severity"], "gray")
        st.markdown(f"### Order {item['order_id']} — :{color}[{item['severity']}]")
        st.write(item["explanation"])
        if item.get("recovery_options"):
            st.write("**Recovery options:**")
            st.table(item["recovery_options"])
        st.divider()