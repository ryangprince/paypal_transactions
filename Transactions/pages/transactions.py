import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import xlsxwriter
import io

st.set_page_config(page_title="Transactions", page_icon="🛒")

st.title("Transaction Breakdown")

filename = st.text_input("Filename", key="filename")
firstname = st.text_input("Enter Name", key="firstname")
highticketstring = st.number_input("Enter High Ticket (integer only)")
uploaded_file = st.file_uploader("Please Upload a CSV File", type=["csv"])

if uploaded_file is not None:
    highticketval = int(highticketstring)
    dfpreclean = pd.read_csv(uploaded_file)

    buffer = io.BytesIO()

    dfpreclean.drop(["Transaction_ID", "Auth_code"], axis=1, inplace=True)
    dfpreclean2 = dfpreclean[dfpreclean["Success"] == 1]
    dfpreclean2.fillna({"Transaction_Notes": "N/A"}, inplace=True)

    dfpreclean2["Day"] = pd.to_datetime(dfpreclean2["Day"])

    """Change the order of the columns."""
    df = dfpreclean2.loc[
        :,
        [
            "Total",
            "Transaction_Type",
            "Type",
            "Country",
            "Source",
            "Day",
            "Customer_Name",
            "Transaction_Notes",
        ],
    ]

    """Get stats for all transactions in the data frame."""

    totalsum = np.sum(df["Total"])
    total_transactions = df["Type"].count()

    mean_transaction = np.mean(df["Total"])
    median_transaction = np.median(df["Total"])
    max_transaction = np.max(df["Total"])

    """Now build out three new data frames: charges only, refund only, charge back only."""

    chargeonlytransactions = df[df["Type"] == "Charge"]
    refundonlytransactions = df[df["Type"] == "Refund"]
    chargebackonlytransactions = df[df["Type"] == "Chargeback"]

    """Initialize date time objects for calculating last 90 days and last 180 days."""

    days90 = pd.to_datetime(date.today() - timedelta(days=90))
    days180 = pd.to_datetime(date.today() - timedelta(days=180))

    """Perform total calculations, total, last 90 days, and last 180 days, for transaction type specific data frames."""

    chargetotal = np.sum(chargeonlytransactions["Total"])
    charge90days = np.sum(
        chargeonlytransactions[chargeonlytransactions["Day"] > days90]["Total"]
    )
    charge180days = np.sum(
        chargeonlytransactions[chargeonlytransactions["Day"] > days180]["Total"]
    )

    refundtotal = np.sum(refundonlytransactions["Total"])
    refund90days = np.sum(
        refundonlytransactions[refundonlytransactions["Day"] > days90]["Total"]
    )
    refund180days = np.sum(
        refundonlytransactions[refundonlytransactions["Day"] > days180]["Total"]
    )

    chargebacktotal = np.sum(chargebackonlytransactions["Total"])
    chargeback90days = np.sum(
        chargebackonlytransactions[chargebackonlytransactions["Day"] > days90]["Total"]
    )
    chargeback180days = np.sum(
        chargebackonlytransactions[chargebackonlytransactions["Day"] > days180]["Total"]
    )

    refundratelifetime = refundtotal / chargetotal
    refundrate90days = refund90days / charge90days
    refundrate180days = refund180days / charge180days

    chargebackratelifetime = refundtotal / chargetotal
    chargebackrate90days = refund90days / charge90days
    chargebackrate180days = refund180days / charge180days

    """Pivot tables."""

    pivottablenames = pd.pivot_table(
        df, index=["Customer_Name"], aggfunc={"Total": np.sum, "Customer_Name": "count"}
    )
    pivottablenames = pivottablenames.rename(
        columns={"Customer_Name": "count_of_total", "Total": "sum_of_total"}
    )
    pivottablenames = pivottablenames.loc[:, ["sum_of_total", "count_of_total"]]
    total_unique_customers = pivottablenames["sum_of_total"].count()

    avg_transactions_count_per_customer = np.mean(pivottablenames["count_of_total"])
    avg_transactions_sum_per_customer = np.mean(pivottablenames["sum_of_total"])

    """Build transaction type specific pivot tables."""

    pivottabletransactiontype = pd.pivot_table(
        df,
        index=["Transaction_Type"],
        aggfunc={"Transaction_Type": "count", "Total": np.sum},
    )
    pivottabletransactiontype["totalpercent"] = (
        pivottabletransactiontype["Total"] / totalsum
    ).apply("{:.2%}".format)

    pivottabletransactioncountry = pd.pivot_table(
        df, index=["Country"], aggfunc={"Country": "count", "Total": np.sum}
    )
    pivottabletransactioncountry["totalpercent"] = (
        pivottabletransactioncountry["Total"] / totalsum
    ).apply("{:.2%}".format)

    """Test locating the transaction for Ryan."""

    namefinal = df[df["Customer_Name"].str.contains(firstname, case=False)]

    """Looking at flagged keywords in Transaction_Notes."""

    payment_note = df[df["Transaction_Notes"].isna() == False]
    flagged_words = "raffle|razz|lottery"
    payment_note_final = df[
        df["Transaction_Notes"].str.contains(flagged_words, case=False)
    ]

    """Highticket: look to see if a customer has a transaction over a certain amount. Normally there a maximum amount a person can transfer, or some other limits."""

    highticket = df[df["Total"] >= highticketval].copy()

    highticket = highticket.sort_values(by="Total", ascending=False)

    """Splitting transactions: sometimes when a person sends an amount over the 
    max threshhold it will split the transactions, with one transaction happening 
    when the transaction is initiated, and then the second part of the transaction 
    coming in a few second/ minutes later.

    Since transactions are logged daily this would show up as a single transaction in the data frame, with an amount that is above the max threshhold.

    NOTE: Some of the code for this part isn't ideal, but for purposes of following along and completing the project I am keeping it as is for now. May review and update later.
    """

    dup = df.copy()

    dup["Customer_Name_next"] = dup["Customer_Name"].shift(1)
    dup["Customer_Name_prev"] = dup["Customer_Name"].shift(-1)

    dup["created_at_day"] = dup["Day"]
    dup["created_at_dayprev"] = dup["Day"].shift(-1)
    dup["created_at_daynext"] = dup["Day"].shift(1)

    dup3 = dup.query(
        "(created_at_day == created_at_dayprev | created_at_day == created_at_daynext) & (Customer_Name == Customer_Name_next | Customer_Name == Customer_Name_prev)"
    )

    """Put all calcuations information into a single data frame (sums, means, etc.)."""

    dfcalc = pd.DataFrame(
        {
            "totalsum": [totalsum],
            "mean_transaction": [mean_transaction],
            "median_transaction": [median_transaction],
            "max_transaction": [max_transaction],
            "total_transactions": [total_transactions],
            "chargetotal": [chargetotal],
            "charge90days": [charge90days],
            "charge180days": [charge180days],
            "refundtotal": [refundtotal],
            "refund90days": [refund90days],
            "refund180days": [refund180days],
            "chargebacktotal": [chargebacktotal],
            "chargeback90days": [chargeback90days],
            "chargeback180days": [chargeback180days],
            "refundratelifetime": [refundratelifetime],
            "refundrate90days": [refundrate90days],
            "refundrate180days": [refundrate180days],
            "chargebackratelifetime": [chargebackratelifetime],
            "chargebackrate90days": [chargebackrate90days],
            "chargebackrate180days": [chargebackrate180days],
            "total_unique_customers": [total_unique_customers],
            "avg_transactions_count_per_customer": [
                avg_transactions_count_per_customer
            ],
            "avg_transactions_sum_per_customer": [avg_transactions_sum_per_customer],
            "90 Days": [days90],
            "180 Days": [days180],
        }
    )

    format_mapping = {
        "totalsum": "${:,.2f}",
        "mean_transaction": "${:,.2f}",
        "median_transaction": "${:,.2f}",
        "max_transaction": "${:,.2f}",
        "total_transactions": "{:,.0f}",
        "chargetotal": "${:,.2f}",
        "charge90days": "${:,.2f}",
        "charge180days": "${:,.2f}",
        "refundtotal": "${:,.2f}",
        "refund90days": "${:,.2f}",
        "refund180days": "${:,.2f}",
        "refundratelifetime": "{:.2%}",
        "refundrate90days": "{:.2%}",
        "refundrate180days": "{:.2%}",
        "chargebacktotal": "${:,.2f}",
        "chargeback90days": "${:,.2f}",
        "chargeback180days": "${:,.2f}",
        "chargebackratelifetime": "{:.2%}",
        "chargebackrate90days": "{:.2%}",
        "chargebackrate180days": "{:.2%}",
        "total_unique_customers": "{:,.0f}",
        "avg_transactions_count_per_customer": "{:,.2f}",
        "avg_transactions_sum_per_customer": "${:,.2f}",
    }

    for key, value in format_mapping.items():
        dfcalc[key] = dfcalc[key].apply(value.format)

    # * build out excel file
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Clean_Data")
        dfcalc.to_excel(writer, sheet_name="Calculations")
        pivottablenames.to_excel(writer, sheet_name="Names")
        pivottabletransactiontype.to_excel(writer, sheet_name="Transaction_Type")
        pivottabletransactioncountry.to_excel(writer, sheet_name="Countries")
        payment_note_final.to_excel(writer, sheet_name="Payment_Notes")
        highticket.to_excel(writer, sheet_name="High_Ticket")
        namefinal.to_excel(writer, sheet_name="Name_checker")
        dup3.to_excel(writer, sheet_name="Double_checker")

        writer.close()

    st.download_button(
        label="Download Excel File",
        data=buffer,
        file_name=f"{st.session_state.file_name}.xlsx",
        mime="application/vnd.ms-excel",
    )

else:
    st.warning("you need to upload a csv")