import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

category_file = "categories.json"
transactions_file = "transactions.csv"  # For saving processed transactions

# Initialize session state
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }
    
# Load saved categories if available
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        try:
            st.session_state.categories = json.load(f)
        except json.JSONDecodeError:
            st.error("Error loading categories file. Using default categories.")
        
def save_categories():
    """Save categories to JSON file"""
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def save_transactions(df):
    """Save processed transactions to CSV"""
    if df is not None:
        df.to_csv(transactions_file, index=False)

def load_saved_transactions():
    """Load previously saved transactions"""
    if os.path.exists(transactions_file):
        try:
            df = pd.read_csv(transactions_file)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            return df
        except Exception as e:
            st.error(f"Error loading saved transactions: {str(e)}")
    return None

def categorize_transactions(df):
    """Apply category rules to transactions"""
    if df is None:
        return None
        
    # Default all to uncategorized
    df["Category"] = "Uncategorized"  # Ensure the Category column exists
    
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        
        for idx, row in df.iterrows():
            # Handle missing or non-string Details
            if pd.isna(row.get("Details", None)) or not isinstance(row.get("Details", ""), str):
                continue
                
            details = row["Details"].lower().strip()
            for keyword in lowered_keywords:
                if keyword in details:
                    df.at[idx, "Category"] = category
                    break
                
    return df  

def clean_dataframe(df):
    """Clean and prepare the dataframe"""
    if df is None:
        return None
        
    # Convert Amount to numeric
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    
    # Drop rows with invalid amounts
    df = df.dropna(subset=["Amount"])
    
    # Ensure Date is datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Drop rows with invalid dates
    df = df.dropna(subset=["Date"])
    
    # Ensure Category column exists
    if "Category" not in df.columns:
        df["Category"] = "Uncategorized"
    
    return df

def load_transactions(file):
    """Load and process transactions from uploaded file"""
    try:
        df = pd.read_csv(file)
        
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        # Check for required columns
        required_columns = ["Date", "Details", "Amount", "Debit/Credit"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            return None
        
        # Clean the dataframe
        df = clean_dataframe(df)
        
        if df is not None and not df.empty:
            # Ensure Category column exists before categorization
            if "Category" not in df.columns:
                df["Category"] = "Uncategorized"
                
            # Now categorize
            df = categorize_transactions(df)
            st.success("File processed successfully!")
            return df
        else:
            st.error("No valid data found in the file.")
            return None
            
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    """Add a keyword to a category for future classification"""
    if not category or not isinstance(keyword, str):
        return False
        
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    
    return False

def main():
    st.title("Simple Finance Dashboard")
    
    # First try to load saved transactions
    df = load_saved_transactions()
    
    # Check for uploaded file
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        if df is not None:
            save_transactions(df)  # Save for future sessions
    
    if df is not None and not df.empty:
        # Make sure the Category column exists
        if "Category" not in df.columns:
            df["Category"] = "Uncategorized"
            
        # Store the full dataframe in session state
        st.session_state.full_df = df.copy()
        
        # Filter for debits and credits
        debits_df = df[df["Debit/Credit"] == "Debit"].copy()
        credits_df = df[df["Debit/Credit"] == "Credit"].copy()
        
        # Store debits in session state (with Category column)
        if not debits_df.empty:
            # Make sure Category column exists in debits_df
            if "Category" not in debits_df.columns:
                debits_df["Category"] = "Uncategorized"
            st.session_state.debits_df = debits_df.copy()
            
        tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
        with tab1:
            if debits_df.empty:
                st.info("No debit transactions found.")
            else:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.success(f"Category '{new_category}' added!")
                        st.rerun()
                
                st.subheader("Your Expenses")
                
                # Ensure all required columns exist before displaying
                display_columns = ["Date", "Details", "Amount", "Category"]
                for col in display_columns:
                    if col not in st.session_state.debits_df.columns:
                        if col == "Category":
                            st.session_state.debits_df["Category"] = "Uncategorized"
                        else:
                            st.error(f"Required column '{col}' is missing!")
                            return
                
                # Now display the dataframe editor
                edited_df = st.data_editor(
                    st.session_state.debits_df[display_columns],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    modified = False
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        
                        # Find this transaction in the full dataframe
                        matches = st.session_state.full_df[
                            (st.session_state.full_df["Date"] == row["Date"]) & 
                            (st.session_state.full_df["Details"] == details)
                        ]
                        
                        if not matches.empty:
                            for match_idx in matches.index:
                                st.session_state.full_df.at[match_idx, "Category"] = new_category
                        
                        # Add the keyword to the category
                        if add_keyword_to_category(new_category, details):
                            modified = True
                    
                    if modified:
                        # Save changes to files
                        save_transactions(st.session_state.full_df)
                        st.success("Changes applied and saved!")
                        st.rerun()
                
                st.subheader('Expense Summary')
                if not st.session_state.debits_df.empty and "Category" in st.session_state.debits_df.columns:
                    category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                    category_totals = category_totals.sort_values("Amount", ascending=False)
                    
                    st.dataframe(
                        category_totals, 
                        column_config={
                         "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR")   
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    fig = px.pie(
                        category_totals,
                        values="Amount",
                        names="Category",
                        title="Expenses by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
        with tab2:
            st.subheader("Payments Summary")
            
            if credits_df.empty:
                st.info("No credit transactions found.")
            else:
                # Get total credits amount
                total_payments = credits_df["Amount"].sum()
                
                # Display metrics
                st.metric("Total Payments", f"{total_payments:,.2f} INR")
                
                # Display credits data
                st.dataframe(
                    credits_df,
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
    else:
        st.info("Please upload a transaction CSV file to get started.")
        st.write("Your file should contain columns: Date, Details, Amount, Debit/Credit")
        
if __name__ == "__main__":
    main()