import streamlit as st
import pandas as pd
from io import BytesIO
import os

# ------------ CONFIG ------------
MAX_CARS = 5            # number of cars
CAR_CAPACITY = 4        # max people per car
DATA_FILE = "guest_data.csv"

# 🔐 Change this before sharing the link
ADMIN_PASSWORD = "wedding2025"   # <--- SET YOUR OWN PASSWORD HERE

HOTEL_NAME = "Godwin"            # fixed stay / pickup location

st.set_page_config(page_title="Wedding Transport Planner", layout="centered")

st.title("🚗 Wedding Transport Planner")

st.markdown(
    f"""
Please fill this form **only if you need transport arranged by the family**.

- Pickup / drop is fixed from: **{HOTEL_NAME}**
- Events covered:
  - Sangeet – 9th – Modi 
  - Wedding – 11th – Regis 
- If you select an event, we will automatically arrange **both:**
  - {HOTEL_NAME} → venue  
  - venue → {HOTEL_NAME}

👉 **One form per person. Please do not submit multiple times.**  
If you make a mistake, contact the organiser instead of filling again.
"""
)

# ------------ HELPERS: SAVE & LOAD BASE DATA (ONE ROW PER PERSON) ------------

def load_base_data():
    """Load base guest data: one row per person."""
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)

        # Ensure required columns exist
        expected_cols = ["Name", "Phone", "Need Sangeet", "Need Wedding"]
        for col in expected_cols:
            if col not in df.columns:
                if col.startswith("Need "):
                    df[col] = False
                else:
                    df[col] = ""

        # Enforce types
        df["Name"] = df["Name"].astype(str)
        df["Phone"] = df["Phone"].astype(str)
        df["Need Sangeet"] = df["Need Sangeet"].fillna(False).astype(bool)
        df["Need Wedding"] = df["Need Wedding"].fillna(False).astype(bool)

        return df[expected_cols]
    else:
        return pd.DataFrame(
            columns=["Name", "Phone", "Need Sangeet", "Need Wedding"]
        )

def save_base_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)


# ------------ CAR ASSIGNMENT HELPERS ------------

def assign_cars_for_event(people_df: pd.DataFrame,
                          to_col_name: str,
                          from_col_name: str) -> pd.DataFrame:
    """
    Assign cars for a single event.
    Each person appears once with two columns:
      - to_col_name: car for Godwin -> venue
      - from_col_name: car for venue -> Godwin
    """
    people_df = people_df.copy()

    if people_df.empty:
        # Ensure columns exist
        people_df[to_col_name] = []
        people_df[from_col_name] = []
        return people_df

    df = people_df.reset_index(drop=True)

    # Initialise columns
    df[to_col_name] = ""
    df[from_col_name] = ""

    # Separate capacity trackers for to/from
    to_loads = {car: 0 for car in range(1, MAX_CARS + 1)}
    from_loads = {car: 0 for car in range(1, MAX_CARS + 1)}

    # Assign TO venue
    for idx in df.index:
        assigned = None
        for car in range(1, MAX_CARS + 1):
            if to_loads[car] + 1 <= CAR_CAPACITY:
                to_loads[car] += 1
                assigned = f"Car {car}"
                break
        if assigned is None:
            assigned = "WAITLIST / NO CAR"
        df.loc[idx, to_col_name] = assigned

    # Assign FROM venue
    for idx in df.index:
        assigned = None
        for car in range(1, MAX_CARS + 1):
            if from_loads[car] + 1 <= CAR_CAPACITY:
                from_loads[car] += 1
                assigned = f"Car {car}"
                break
        if assigned is None:
            assigned = "WAITLIST / NO CAR"
        df.loc[idx, from_col_name] = assigned

    return df


# ------------ GUEST FORM (VISIBLE TO EVERYONE) ------------

st.subheader("Guest Details Form")

with st.form("guest_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Full Name*")
        phone = st.text_input("Phone Number* (for coordination on the day)")

    with col2:
        need_sangeet = st.checkbox("I need transport for Sangeet – 9th – Modi")
        need_wedding = st.checkbox("I need transport for Wedding – 11th – Regis")

    st.markdown(
        """
- If you tick **Sangeet**, we will arrange: Godwin → Modi and Modi → Godwin.  
- If you tick **Wedding**, we will arrange: Godwin → Regis and Regis → Godwin.
"""
    )

    submitted = st.form_submit_button("Submit")

    if submitted:
        if not name.strip():
            st.error("Please enter your name.")
        elif not phone.strip():
            st.error("Please enter your phone number.")
        elif not (need_sangeet or need_wedding):
            st.error("Please select at least one event for transport.")
        else:
            base_df = load_base_data()
            name_clean = name.strip()
            phone_clean = phone.strip()

            # Sanitize existing data for comparison
            if not base_df.empty:
                base_df["Name"] = base_df["Name"].astype(str)
                base_df["Phone"] = base_df["Phone"].astype(str)

            # Check for duplicate (same name + phone)
            duplicate_mask = (
                (base_df["Name"].str.strip().str.lower() == name_clean.lower())
                & (base_df["Phone"].str.strip() == phone_clean)
            ) if not base_df.empty else pd.Series([], dtype=bool)

            if duplicate_mask.any():
                st.error(
                    "We already have a response for this name and phone number. "
                    "Please contact the organiser if you need to make changes."
                )
            else:
                new_row = {
                    "Name": name_clean,
                    "Phone": phone_clean,
                    "Need Sangeet": bool(need_sangeet),
                    "Need Wedding": bool(need_wedding),
                }
                base_df = pd.concat(
                    [base_df, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                save_base_data(base_df)
                st.success(
                    "Thank you! Your transport preference has been recorded ✅\n\n"
                    "Please do not submit the form again."
                )


st.markdown("---")

# ------------ ADMIN AREA (ONLY YOU) ------------

st.sidebar.subheader("Organiser Login")
admin_input = st.sidebar.text_input("Admin password", type="password")
is_admin = admin_input == ADMIN_PASSWORD

if is_admin:
    st.subheader("👑 Organiser Area – Guests & Car Assignments")

    base_df = load_base_data()
    if base_df.empty:
        st.info("No guest data yet.")
    else:
        # 1) Master list: one row per person
        st.markdown("### Master Guest List (one row per person)")
        st.dataframe(base_df, use_container_width=True)

        # 2) Sangeet event list (one row per person, 2 car columns)
        sangeet_people = base_df[base_df["Need Sangeet"] == True][["Name", "Phone"]]
        sangeet_assigned = assign_cars_for_event(
            sangeet_people,
            to_col_name="Car To Modi (Godwin → Modi)",
            from_col_name="Car From Modi (Modi → Godwin)",
        )

        # 3) Wedding event list (one row per person, 2 car columns)
        wedding_people = base_df[base_df["Need Wedding"] == True][["Name", "Phone"]]
        wedding_assigned = assign_cars_for_event(
            wedding_people,
            to_col_name="Car To Regis (Godwin → Regis)",
            from_col_name="Car From Regis (Regis → Godwin)",
        )

        st.markdown("### Sangeet – 9th – Modi (one row per person)")
        st.dataframe(sangeet_assigned, use_container_width=True)

        st.markdown("### Wedding – 11th – Regis (one row per person)")
        st.dataframe(wedding_assigned, use_container_width=True)

        # Create Excel with separate sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            base_df.to_excel(writer, index=False, sheet_name="Master_List")
            sangeet_assigned.to_excel(writer, index=False, sheet_name="Sangeet")
            wedding_assigned.to_excel(writer, index=False, sheet_name="Wedding")
        output.seek(0)

        st.download_button(
            label="📥 Download Excel (Master + Sangeet + Wedding)",
            data=output,
            file_name="wedding_car_assignments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.warning("Danger zone: This will delete all stored guest responses.")
        if st.button("❌ Clear ALL guest data"):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.success("All guest data deleted.")
else:
    st.info(
        "If you are the organiser, use the admin password in the sidebar to see the full data and download Excel."
    )
