# frontend/app.py

import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from io import BytesIO

# Configuration for the FastAPI backend
# If running locally, it's usually http://127.0.0.1:8000
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Receipt Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧾 Receipt & Bill Analyzer")
st.markdown("Upload your receipts and bills to extract data and get insights!")

# --- Helper Functions for API Calls ---
def upload_file_to_backend(file):
    """Sends the file to the backend for upload and processing."""
    files = {"file": (file.name, file.getvalue(), file.type)}
    try:
        response = requests.post(f"{BACKEND_URL}/upload-receipt/", files=files)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error uploading file: {e}")
        if response is not None:
            st.error(f"Backend response: {response.text}")
        return None

def fetch_all_receipts():
    """Fetches all receipts from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/receipts/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching receipts: {e}")
        return []

def fetch_insights():
    """Fetches aggregated insights from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/insights/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching insights: {e}")
        return {}

def update_receipt_in_backend(receipt_id, data):
    """Updates a receipt in the backend."""
    try:
        response = requests.put(f"{BACKEND_URL}/receipts/{receipt_id}", json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error updating receipt {receipt_id}: {e}")
        return None

def delete_receipt_from_backend(receipt_id):
    """Deletes a receipt from the backend."""
    try:
        response = requests.delete(f"{BACKEND_URL}/receipts/{receipt_id}")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting receipt {receipt_id}: {e}")
        return False

# --- Sidebar for Navigation ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Upload & View", "Insights & Analytics"])

# --- Main Content Area ---

if page == "Upload & View":
    st.header("Upload New Receipt")
    uploaded_file = st.file_uploader(
        "Choose a file (JPG, PNG, PDF, TXT)",
        type=["jpg", "jpeg", "png", "pdf", "txt"]
    )

    if uploaded_file is not None:
        with st.spinner("Processing file... This may take a moment."):
            result = upload_file_to_backend(uploaded_file)
            if result:
                st.success("File uploaded and processed successfully!")
                st.json(result) # Show raw parsed data for debugging
                st.write("---")
            else:
                st.error("Failed to process the uploaded file.")

    st.header("All Uploaded Receipts")

    # Fetch and display receipts
    receipts_data = fetch_all_receipts()

    if receipts_data:
        # Convert transaction_date and uploaded_at strings to datetime objects for proper display/sorting
        df = pd.DataFrame(receipts_data)
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df["uploaded_at"] = pd.to_datetime(df["uploaded_at"])

        # Display tabular view
        st.subheader("Tabular View of Receipts")
        st.dataframe(df.set_index('id'))

        # Manual Correction / Edit Feature
        st.subheader("Edit/Delete Receipt")
        receipt_ids = [r['id'] for r in receipts_data]
        if receipt_ids:
            selected_id = st.selectbox("Select Receipt ID to Edit/Delete", receipt_ids)
            selected_receipt = next((r for r in receipts_data if r['id'] == selected_id), None)

            if selected_receipt:
                with st.expander(f"Edit Receipt ID: {selected_id}"):
                    # Display original file if it's an image
                    if selected_receipt['filename'].lower().endswith(('.png', '.jpg', '.jpeg')):
                        file_url = f"{BACKEND_URL}/uploads/{selected_receipt['filename']}"
                        st.image(file_url, caption=f"Original File: {selected_receipt['filename']}", use_column_width=True)
                    else:
                        st.info(f"Original file: {selected_receipt['filename']}")

                    col1, col2 = st.columns(2)
                    new_vendor = col1.text_input("Vendor", value=selected_receipt['vendor'], key=f"vendor_{selected_id}")
                    new_amount = col2.number_input("Amount", value=float(selected_receipt['amount']), format="%.2f", key=f"amount_{selected_id}")

                    col3, col4 = st.columns(2)
                    # Convert datetime to date for date_input widget
                    tx_date_dt = selected_receipt['transaction_date']
                    if isinstance(tx_date_dt, str):
                        tx_date_dt = datetime.fromisoformat(tx_date_dt.replace('Z', '+00:00')) # Handle 'Z' for UTC
                    new_transaction_date = col3.date_input("Transaction Date", value=tx_date_dt.date(), key=f"date_{selected_id}")
                    new_category = col4.text_input("Category", value=selected_receipt['category'], key=f"category_{selected_id}")

                    if st.button(f"Save Changes for ID {selected_id}", key=f"save_{selected_id}"):
                        update_data = {
                            "vendor": new_vendor,
                            "amount": new_amount,
                            "transaction_date": datetime.combine(new_transaction_date, datetime.min.time()).isoformat(), # Convert date back to datetime string
                            "category": new_category
                        }
                        updated_receipt = update_receipt_in_backend(selected_id, update_data)
                        if updated_receipt:
                            st.success(f"Receipt ID {selected_id} updated successfully!")
                            st.experimental_rerun() # Rerun to refresh the list

                if st.button(f"Delete Receipt ID {selected_id}", key=f"delete_{selected_id}", type="secondary"):
                    if st.warning(f"Are you sure you want to delete receipt ID {selected_id}? This action cannot be undone."):
                        if st.button("Confirm Delete", key=f"confirm_delete_{selected_id}"):
                            if delete_receipt_from_backend(selected_id):
                                st.success(f"Receipt ID {selected_id} deleted successfully.")
                                st.experimental_rerun() # Rerun to refresh the list
                            else:
                                st.error(f"Failed to delete receipt ID {selected_id}.")
        else:
            st.info("No receipts uploaded yet. Upload one to see it here!")

    else:
        st.info("No receipts found. Upload one to get started!")

elif page == "Insights & Analytics":
    st.header("Statistical Insights & Visualizations")

    insights = fetch_insights()

    if insights:
        st.subheader("Overall Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spend", f"₹{insights.get('total_spend', 0):,.2f}")
        col2.metric("Average Spend", f"₹{insights.get('mean_spend', 0):,.2f}")
        col3.metric("Median Spend", f"₹{insights.get('median_spend', 0):,.2f}")
        st.write(f"**Mode Spend:** {', '.join([f'₹{m:,.2f}' for m in insights.get('mode_spend', [])])}")

        st.subheader("Top Vendors")
        top_vendors_df = pd.DataFrame(insights.get("top_vendors", []), columns=["Vendor", "Count"])
        if not top_vendors_df.empty:
            st.dataframe(top_vendors_df, hide_index=True)
            fig_vendor, ax_vendor = plt.subplots(figsize=(10, 6))
            sns.barplot(x="Count", y="Vendor", data=top_vendors_df, ax=ax_vendor, palette="viridis")
            ax_vendor.set_title("Top Vendors by Frequency")
            ax_vendor.set_xlabel("Number of Receipts")
            ax_vendor.set_ylabel("Vendor")
            st.pyplot(fig_vendor)
        else:
            st.info("No vendor data to display.")

        st.subheader("Category Distribution")
        category_dist = insights.get("category_distribution", {})
        if category_dist:
            category_df = pd.DataFrame(list(category_dist.items()), columns=["Category", "Count"])
            st.dataframe(category_df, hide_index=True)

            fig_category, ax_category = plt.subplots(figsize=(10, 6))
            # Use autopct to show percentage on pie chart slices
            ax_category.pie(category_df["Count"], labels=category_df["Category"], autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
            ax_category.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
            ax_category.set_title("Expenditure by Category")
            st.pyplot(fig_category)
        else:
            st.info("No category data to display.")


        st.subheader("Monthly Spend Trend")
        monthly_trend = insights.get("monthly_spend_trend", {})
        if monthly_trend:
            monthly_df = pd.DataFrame(list(monthly_trend.items()), columns=["Month", "Spend"])
            monthly_df["Month"] = pd.to_datetime(monthly_df["Month"]) # Convert to datetime for proper sorting
            monthly_df = monthly_df.sort_values("Month")

            fig_monthly, ax_monthly = plt.subplots(figsize=(12, 6))
            sns.lineplot(x="Month", y="Spend", data=monthly_df, marker='o', ax=ax_monthly, color='skyblue')
            ax_monthly.set_title("Monthly Expenditure Trend")
            ax_monthly.set_xlabel("Month")
            ax_monthly.set_ylabel("Total Spend (₹)")
            ax_monthly.tick_params(axis='x', rotation=45)
            ax_monthly.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig_monthly)
        else:
            st.info("No monthly spend data to display.")

        st.subheader("Yearly Spend Trend")
        yearly_trend = insights.get("yearly_spend_trend", {})
        if yearly_trend:
            yearly_df = pd.DataFrame(list(yearly_trend.items()), columns=["Year", "Spend"])
            yearly_df["Year"] = pd.to_datetime(yearly_df["Year"], format="%Y") # Convert to datetime for proper sorting
            yearly_df = yearly_df.sort_values("Year")

            fig_yearly, ax_yearly = plt.subplots(figsize=(10, 6))
            sns.lineplot(x="Year", y="Spend", data=yearly_df, marker='o', ax=ax_yearly, color='lightcoral')
            ax_yearly.set_title("Yearly Expenditure Trend")
            ax_yearly.set_xlabel("Year")
            ax_yearly.set_ylabel("Total Spend (₹)")
            ax_yearly.tick_params(axis='x', rotation=45)
            ax_yearly.grid(True, linestyle='--', alpha=0.7)
            st.pyplot(fig_yearly)
        else:
            st.info("No yearly spend data to display.")

    else:
        st.info("Upload some receipts to generate insights!")

