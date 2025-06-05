import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Streamlit page config
st.set_page_config(page_title="PARA Membership Dataset Viewer", layout="wide")
st.title("📊 PARA Membership Dataset Viewer")
st.markdown("Reads `PARA_dataset.xlsx` as the official list and saves additions separately in `user_added_entries.csv`.")

# File paths
excel_filename = "PARA_dataset.xlsx"
user_added_file = "user_added_entries.csv"

# Trigger sidebar reset logic
if "manual_form_submitted" not in st.session_state:
    st.session_state.manual_form_submitted = False

if st.session_state.manual_form_submitted:
    for field in ["name_input", "call_sign_input", "location_input", "club_input", "search_term"]:
        st.session_state[field] = ""
    st.session_state.manual_form_submitted = False
    st.rerun()

# Sidebar Header
st.sidebar.header("Options")
refresh_button = st.sidebar.button("🔄 Refresh Official List")

# Load Excel
@st.cache_data(show_spinner=False)
def load_official_dataset(filepath):
    try:
        xls = pd.ExcelFile(filepath)
        all_dfs = []
        all_columns = set()
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            all_columns.update(df.columns)
        all_columns = list(all_columns)
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df = df.dropna(how='all')
            first_col = df.columns[0]
            df = df[~df[first_col].astype(str).str.contains(r'\bID\s*(#|No\.?)\b', case=False, na=False)]
            df = df.reindex(columns=all_columns)
            df["Membership Type"] = sheet
            all_dfs.append(df)
        return pd.concat(all_dfs, ignore_index=True)
    except Exception as e:
        st.error(f"❌ Error reading Excel: {e}")
        return pd.DataFrame()

# Load user-added entries
def load_user_entries():
    if os.path.exists(user_added_file):
        return pd.read_csv(user_added_file)
    return pd.DataFrame()

# Save entry
def save_user_entry(entry_dict):
    entry_dict["Timestamp"] = datetime.now().isoformat()
    new_df = pd.DataFrame([entry_dict])
    if os.path.exists(user_added_file):
        existing_df = pd.read_csv(user_added_file)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
    combined_df.to_csv(user_added_file, index=False)

# Load data
if os.path.exists(excel_filename):
    if refresh_button or "official_data" not in st.session_state:
        st.session_state.official_data = load_official_dataset(excel_filename)

    df_official = st.session_state.official_data.copy()
    df_user = load_user_entries()

    # --- Sidebar: Search and Add Entry ---
    st.sidebar.subheader("🔍 Search Official List")
    search_term = st.sidebar.text_input("Enter keyword to search", key="search_term")
    if search_term:
        filtered_official = df_official[df_official.apply(
            lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
    else:
        filtered_official = df_official

    st.sidebar.subheader("➕ Add New Entry")
    with st.sidebar.form("manual_entry_form"):
        name = st.text_input("Name", key="name_input")
        call_sign = st.text_input("Call Sign", key="call_sign_input")
        location = st.text_input("Location", key="location_input")
        club = st.text_input("Club", key="club_input")
        submit_manual = st.form_submit_button("Add Manually")

        if submit_manual and name and call_sign:
            entry = {
                "Name": name,
                "Call Sign": call_sign,
                "Location": location,
                "Club": club,
                "Timestamp": datetime.now().isoformat()
            }
            save_user_entry(entry)
            st.sidebar.success("✅ Entry added to user list.")

            # Trigger full reset of sidebar fields
            st.session_state.manual_form_submitted = True
            st.rerun()

    # Main area — display filtered official data
    st.subheader("📘 Official PARA Members List")
    st.success(f"Showing {len(filtered_official)} official record(s)")
    st.dataframe(filtered_official, use_container_width=True)

    # Add from search result
    if search_term:
        st.subheader("📌 Add from Search Results to User List")

        if filtered_official.empty:
            st.warning("No matching records found for the search term.")
        else:
            filtered_official_reset = filtered_official.reset_index(drop=True)
            filtered_official_reset.columns = filtered_official_reset.columns.str.strip().str.title()

            if 'Call Sign' in filtered_official_reset.columns:
                call_signs = filtered_official_reset['Call Sign'].fillna("Unknown Callsign").tolist()
                selected_callsigns = st.multiselect("Select rows to add (Call Sign)", options=call_signs)

                if st.button("Add Selected"):
                    for cs in selected_callsigns:
                        matched_rows = filtered_official_reset[filtered_official_reset['Call Sign'] == cs]
                        for _, row in matched_rows.iterrows():
                            entry_dict = row.to_dict()
                            entry_dict.pop("Timestamp", None)
                            save_user_entry(entry_dict)
                    st.success("✅ Selected entries added to user list.")
                    df_user = load_user_entries()
            else:
                st.error("⚠️ 'Call Sign' column not found in filtered data.")
    else:
        st.info("Search to filter and add from official list.")

    # Display user-added data
    st.subheader("🗃️ User-Added Entries")
    if not df_user.empty:
        st.info(f"{len(df_user)} user-added record(s)")
        st.dataframe(df_user, use_container_width=True)

        csv_user = df_user.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download User List", data=csv_user, file_name="user_added_entries.csv", mime="text/csv")
    else:
        st.warning("No user-added entries yet.")

    # Download official list
    csv_official = filtered_official.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Official Filtered List", data=csv_official, file_name="official_filtered_members.csv", mime="text/csv")

else:
    st.error(f"❌ File `{excel_filename}` not found in the current directory.")
