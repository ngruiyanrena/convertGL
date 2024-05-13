import streamlit as st
import pandas as pd
import re

def debit_credit(row):
    debit_categories = ['asset', 'expense']
    credit_categories = ['liability', 'revenue', 'equity']

    debit = credit = 0

    if any(cat in row['Account Type'].lower() for cat in debit_categories):
        if row['Amount'] >= 0:
            debit = row['Amount']
        else:
            credit = -row['Amount']  # Make it positive as credit
    elif any(cat in row['Account Type'].lower() for cat in credit_categories):
        if row['Amount'] >= 0:
            credit = row['Amount']
        else:
            debit = -row['Amount']  # Make it positive as debit

    return pd.Series([debit, credit])

def alphanumeric_key(s):
    if pd.isna(s):
        return (1, s)
    s = str(s)
    return (0, [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)])

def process_GL(GL_file, COA_file):
    GL_data = pd.read_excel(GL_file, header=4)
    GL_cleaned = GL_data.rename(columns={ GL_data.columns[0]: "Account" })
    GL_cleaned['Account'].ffill(inplace=True)
    GL_cleaned.dropna(subset=['Transaction Type'], inplace=True)
    GL_cleaned[['Account Code', 'Account Name']] = GL_cleaned['Account'].str.extract(r'(?:(\d+(?:\.\d+)*)\s+)?(.*)')
    GL_cleaned['Account Name'] = GL_cleaned['Account Name'].astype(str)
    GL_cleaned['Account Name'] = GL_cleaned['Account Name'].apply(
        lambda x: re.sub(r' - .+$', '', x) if x.startswith('Trade and other payables') else x
    )

    COA_data = pd.read_excel(COA_file, sheet_name="Chart of Accounts", header=0, dtype=str)
    COA_cleaned = COA_data[['Account Type*', 'Name*', 'Code']]
    COA_cleaned.rename(columns={'Account Type*': 'Account Type'}, inplace=True)
    COA_cleaned.rename(columns={'Name*': 'Account Name'}, inplace=True)
    COA_cleaned.rename(columns={'Code': 'Account Code'}, inplace=True)

    GL_cleaned = GL_cleaned.merge(COA_cleaned, 
                                  on=['Account Name'], 
                                  how='left')
    
    GL_cleaned['Account Type'] = GL_cleaned['Account Type'].astype(str)
    GL_cleaned[['Debit', 'Credit']] = GL_cleaned.apply(debit_credit, axis=1)

    GL_cleaned.sort_values(by=['No.'], key=lambda x: x.map(alphanumeric_key), ascending=True, inplace=True)
    
    output_df = pd.DataFrame({
        "Journal Reference": GL_cleaned['No.'],
        "Contact": GL_cleaned['Name'],
        "Date": GL_cleaned['Date'],
        "Account": GL_cleaned['Account'],
        "Description": GL_cleaned['Memo/Description'],
        "Tax Included in Amount": GL_cleaned['GST Code'],
        "Debit Amount (SGD)": GL_cleaned['Debit'],
        "Credit Amount (SGD)": GL_cleaned['Credit'],
        "Amount": GL_cleaned['Amount'],
        "Account Type": GL_cleaned['Account Type'],
        "Transaction Type": GL_cleaned['Transaction Type'],
        "Exchange Rate": GL_cleaned['Exchange Rate'],
        "Currency": GL_cleaned['Currency'],
        "Foreign Amount": GL_cleaned['Foreign Amount']
    })
    
    return output_df


def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def main():

    st.title('Convert GL into Import Journals')

    GL_file = st.file_uploader("Upload General Ledger", type=['xlsx'])
    COA_file = st.file_uploader("Upload COA Import", type=['xlsx'])

    if GL_file and COA_file is not None:
        processed_data = process_GL(GL_file, COA_file)
        st.write("Processed Data", processed_data)
        csv = convert_df_to_csv(processed_data)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='Transactions.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()