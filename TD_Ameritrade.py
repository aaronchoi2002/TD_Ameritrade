# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 11:46:17 2023

@author: USER
"""

import warnings
import pandas as pd 
import datetime
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
from datetime import date
import streamlit as st 
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import yfinance as yf 
import numpy as np
st.set_page_config(layout="wide")

def drawndown(df_result):
    max_return, list_drawn_down  = [0], []
    for index,row in df_result.iterrows():
        max_return.append(row["累算盈虧"])
        drawn_down = row["累算盈虧"] - max(max_return)
        list_drawn_down.append(drawn_down)
    return list_drawn_down



st.title('TD_Ameritrade statistic')
st.header("CSV File Upload")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
load = st.button("Load Data")

#modifty dataframe

if "load_state" not in st.session_state:
    st.session_state.load_state = False


if load or st.session_state.load_state:
    st.session_state.load_state = True
    
    if uploaded_file is not None:
    
        df = pd.read_csv(uploaded_file)
        df.dropna(subset=["DESCRIPTION"], inplace=True)
        df["日期"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
        length_all = len(df)
        
        #classify option transaction or other item 
        df_other = df[(df["SYMBOL"].isnull()) | (df["COMMISSION"].isnull()) |(df["REG FEE"].isnull())] 
        df_order = df[(df["SYMBOL"].notnull()) & (df["COMMISSION"].notnull()) & (df["REG FEE"].notnull())]
        
        length_other = len(df_other)
        length_option_transaction = len(df_order)
        
        #modify order
        
        df_order["买/卖"] = df_order["DESCRIPTION"].apply(lambda x:x.split(" ")[0])
        df_order["履约价格"] = df_order["DESCRIPTION"].apply(lambda x:float(x.split(" ")[6]))
        df_order["股票代碼"] = df_order["SYMBOL"].apply(lambda x:x.split(" ")[0])
        df_order["认购/认沽"] = df_order["SYMBOL"].apply(lambda x:x.split(" ")[5])
        df_order["手續費"] = - df_order["REG FEE"] - df_order["COMMISSION"]
        
        df_order["到期日_Y"] = df_order["SYMBOL"].apply(lambda x:x.split(" ")[3])
        df_order["到期日_M"] = df_order["SYMBOL"].apply(lambda x:x.split(" ")[2])
        df_order["到期日_D"] = df_order["SYMBOL"].apply(lambda x:x.split(" ")[1])
        df_order["到期日"] = df_order["到期日_D"] +"/"+ df_order["到期日_M"] +"/"+ df_order["到期日_Y"]
        df_order["到期日"] = pd.to_datetime(df_order["到期日"], format="%b/%d/%Y")
        df_order["日期"] = pd.to_datetime(df_order["DATE"], format="%m/%d/%Y")
        
        df_order.rename(columns={"TRANSACTION ID":"订单序号","QUANTITY":"数量","PRICE":"期权金","AMOUNT":"淨期权金"},inplace=True)
        df_order = df_order[['日期','订单序号','买/卖','认购/认沽','股票代碼','数量','期权金',"手續費",'淨期权金','履约价格',"到期日"]]
        
        df_order.loc[(df_order["买/卖"] == 'Bought'),"买/卖"] = '买'
        df_order.loc[(df_order["买/卖"] == 'Sold'),"买/卖"] = '卖'
        df_order.loc[(df_order["认购/认沽"] == 'Put'),"认购/认沽"] = '认沽'
        df_order.loc[(df_order["认购/认沽"] == 'Call'),"认购/认沽"] = '认购'
        
        df_order_buy = df_order[df_order["买/卖"] == "买"]
        df_order_sell = df_order[df_order["买/卖"] == "卖"]
        
        df_order_sell_join = pd.merge(df_order_sell,df_order_buy, how='left', on=['股票代碼','履约价格','到期日'], suffixes=('_卖', '_买'))#left join
        
        # Handle partial settlement - sell
        list_order_number_buy =[]
        list_order_number_sell =[]
        duplicate_order_sell = []
        for index,row in df_order_sell_join.iterrows():
          if row.订单序号_卖 in list_order_number_sell:
            df_order_sell_join.at[index,"淨期权金_卖"] =0
            df_order_sell_join.at[index,"手續費_卖"] =0
            duplicate_order_sell.append(row.订单序号_卖)
        
          # elif row.订单序号_买 in list_order_number_buy:
          #     df_order_sell_join.at[index,"淨期权金_买"] =0
          #     df_order_sell_join.at[index,"手續費_买"] =0
          #     df_order_sell_join.append(row.订单序号_买)
        
          else:
             list_order_number_sell.append(row.订单序号_卖)
             list_order_number_buy.append(row.订单序号_买)
        
            
        df_order_sell_join["交易種類"] = "0"    
        df_order_sell_match = df_order_sell_join[(df_order_sell_join["日期_买"].notnull())]
        df_order_sell_non_match = df_order_sell_join[(df_order_sell_join["日期_买"].isnull())]
        
        df_order_buy_join = pd.merge(df_order_sell,df_order_buy, how='right', on=['股票代碼','履约价格','到期日'], suffixes=('_卖', '_买')) #right join
        # Handle partial settlement  - buy
        list_order_number_buy =[]
        duplicate_order_buy = []
        for index,row in df_order_buy_join.iterrows():
          if row.订单序号_买 in list_order_number_buy:
            df_order_buy_join.at[index,"淨期权金_买"] =0
            df_order_buy_join.at[index,"手續費_买"] =0
            duplicate_order_buy.append(row.订单序号_买)
          else:
            list_order_number_buy.append(row.订单序号_买)
        
        
        df_order_buy_match = df_order_buy_join[(df_order_buy_join["日期_卖"].notnull())]
        df_order_buy_non_match = df_order_buy_join[(df_order_buy_join["日期_卖"].isnull())]
        
        # record lenght 
        length_sell_total = (len(df_order_sell_join)) #left join
        length_sell_match = (len(df_order_sell_match))
        length_sell_non_match = (len(df_order_sell_non_match))
        length_buy_total = (len(df_order_buy_join)) #right join
        length_buy_match = (len(df_order_buy_match))
        length_buy_non_match = (len(df_order_buy_non_match))
        
        #left join - match handle
        for index,row in df_order_sell_match.iterrows():
          if (row.数量_卖 - row.数量_买) != 0:
            df_order_sell_match.at[index,"交易種類"] ="分段平倉(到期/手動)"
          else:
            df_order_sell_match.at[index,"交易種類"] ="平倉"
        
        #check which position is open position 
        df_order_sell_match["開倉"] = "0"
        df_order_sell_match["持倉日期"] = 0
        
        for index,row in df_order_sell_match.iterrows():
          if (row.日期_卖 <= row.日期_买):
            df_order_sell_match.at[index,"開倉"] = "卖单"
            df_order_sell_match.at[index,"持倉日期"] = (row.日期_买 - row.日期_卖).days
          else:
            df_order_sell_match.at[index,"開倉"] = "买单"
            df_order_sell_match.at[index,"持倉日期"] = (row.日期_卖 - row.日期_买).days
            print(index)
        
        
        
        
        #left join - non match handle
        #check settled
        df_order_sell_non_match["交易種類"] = df_order_sell_non_match["到期日"].apply(lambda x: "到期" if x.date() < date.today() else "未平倉")
        df_order_sell_non_match["淨期权金_买"] = 0
        
        #check which position is open position 
        df_order_sell_non_match["開倉"] = "0"
        df_order_sell_non_match["持倉日期"] = 0
        for index,row in df_order_sell_non_match.iterrows():
          df_order_sell_non_match.at[index,"開倉"] = "卖单"
          df_order_sell_non_match.at[index,"持倉日期"] = (row.到期日 - row.日期_卖).days
        
        
        
        #combine partial tr
        frame = [df_order_sell_match, df_order_sell_non_match]
        df_order_modified = pd.concat(frame)
        df_order_modified.sort_values(by="日期_卖", ascending=True, inplace=True)
        df_order_modified["手續費_卖"] = round(df_order_modified["手續費_卖"],2)
        df_order_modified = df_order_modified[['日期_卖','日期_买','股票代碼','履约价格','到期日','认购/认沽_卖','数量_卖','期权金_卖','手續費_卖','淨期权金_卖','数量_买','期权金_买','手續費_买',"淨期权金_买",'订单序号_卖','订单序号_买','交易種類',"持倉日期"]]
        
        #Other - fund in out
        fund_in_out = df_other[df_other["DESCRIPTION"] == "WIRE INCOMING"]
        fund_in_out.rename(columns={"DESCRIPTION":"簡介","AMOUNT":"數額"},inplace=True)
        fund_in_out = fund_in_out[["日期","簡介","數額"]]
        fund_in_out_sum = sum(fund_in_out["數額"])
        
        
        
        #statistic
        df_order_modified["盈亏"] = df_order_modified["淨期权金_卖"] + df_order_modified["淨期权金_买"]
        
        #combine partial settle trade 
        combine_partial = df_order_modified.groupby("订单序号_卖")
        combine_partial = pd.DataFrame(combine_partial.sum()['盈亏'])
        
        
        option_pnl = sum(combine_partial["盈亏"]) # include floating 
        option_pnl_settled = sum(df_order_modified[df_order_modified["交易種類"] !="未平倉"]["盈亏"]) # include floating 
        best_trade = max(combine_partial["盈亏"])
        worst_trade = min(combine_partial["盈亏"])
        Longest_trade = max(df_order_modified["持倉日期"])
        number_of_trade = len(df_order_modified) - len(duplicate_order_sell)
        win_num = (len(combine_partial[combine_partial["盈亏"] >0]))
        loss_num = (len(combine_partial[combine_partial["盈亏"] <0]))
        # win_loss_ratiio = (win_rate/loss_rate) *100
        reward_ratio = sum(df_order_modified.loc[df_order_modified['盈亏'] > 0]["盈亏"])/len(df_order_modified[df_order_modified["盈亏"] >0])
        risk_ratio = sum(df_order_modified.loc[df_order_modified['盈亏'] < 0]["盈亏"])/len(df_order_modified[df_order_modified["盈亏"] <0])
        risk_reward_ratio = (reward_ratio/(-risk_ratio))*100
        period = (df_order_modified.日期_卖.iloc[-1] - df_order_modified.日期_卖.iloc[0]).days
        
        accumulated_return = 0
        df_order_modified["累算盈虧"] = df_order_modified["盈亏"].cumsum()
        # list_accumulated_return = []  
        # for index,row in df_order_modified.iterrows():
        #     accumulated_return = row["盈亏"] + accumulated_return
        #     df_order_modified.at[index,"累算盈虧"] = accumulated_return
        #     list_accumulated_return.append(accumulated_return)
        
        df_order_modified["最大回撤"] = drawndown(df_order_modified)
        max_dawndown = min(drawndown(df_order_modified))
        
        #Result by stock 
        option_result = df_order_modified[["日期_卖","股票代碼","交易種類","持倉日期","履约价格","数量_卖","盈亏"]]
        stock_ratio = option_result.groupby("股票代碼")
        option_result_by_stock = pd.DataFrame(stock_ratio.sum()['盈亏'])
        df_order_modified["stock_value"] = df_order_modified["数量_卖"]*100 * df_order_modified["履约价格"]
        
        
        #commission 
        df_order_modified=  df_order_modified.fillna(0)
        df_order_modified["總手續費"] = df_order_modified["手續費_卖"] + df_order_modified["手續費_买"]
        total_commission = sum(df_order_modified["總手續費"])    
        st.caption(f"交易期: {min(df_order_modified.日期_卖)} - {max(df_order_modified.日期_卖)} ")
        
        
        #% of return 
        fund_in_out.sort_values(by="日期", ascending=True, inplace=True,)
        fund_in_out["總出入金"] = fund_in_out.數額.cumsum()
        fund_in_out.sort_values(by="日期", ascending=False, inplace=True)
        start_date = df_order_modified["日期_卖"].iloc[0]
        start_amount = fund_in_out["數額"].iloc[-1]
        inital_fund_in_out = {'日期':start_date, '簡介':"inital_amount", '數額':start_amount, '總出入金':start_amount}
        fund_in_out = fund_in_out.append(inital_fund_in_out, ignore_index=True)
        
        
        df_order_modified.sort_values(by="日期_卖", ascending=False, inplace=True)
        fund_in = []
        for index,row in df_order_modified.iterrows():
          for index1,row1 in fund_in_out.iterrows():
            if (row.日期_卖 >= row1.日期):
              fund_in.append(row1.總出入金)
              break
        df_order_modified["fund_in"] = fund_in
        
        df_order_modified.sort_values(by="日期_卖", ascending=True, inplace=True)
        df_order_modified["累算盈虧"] = df_order_modified["盈亏"].cumsum()
        df_order_modified["fund_in_diff"] =df_order_modified.fund_in - df_order_modified.fund_in.shift()
        df_order_modified["fund_in_diff"].iloc[0] = df_order_modified["fund_in"].iloc[0] -0
        df_order_modified["account_summary"] = (df_order_modified["盈亏"] + df_order_modified["fund_in_diff"]).cumsum()
        df_order_modified["盈亏_%"] = df_order_modified["盈亏"]/df_order_modified["account_summary"]
        df_order_modified["累算盈虧_%"] = df_order_modified["盈亏_%"].cumsum()
        return_per = df_order_modified["累算盈虧_%"].iloc[-1]
        
        
        #branchmark9
        branchmark = yf.download("^GSPC", start=min(df_order_modified.日期_卖), end=max(df_order_modified.日期_卖)).reset_index()
        rel=branchmark["Adj Close"].pct_change()
        cumret = (1+rel).cumprod()-1
        cumret = cumret.fillna(0)
        
        
        
        
        tab1, tab2, tab3, tab4 = st.tabs(["期权", "未平倉", "出入金紀錄", "數據紀錄"])
        
        
        with tab1:
            with st.expander("点击展开 (图表)", expanded=False):
        
                st.title("總期权金回報")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                      x=df_order_modified["日期_卖"],
                      y=df_order_modified["累算盈虧_%"]*100, name="總期权金回報"))
                fig.add_trace(go.Scatter(
                      x=branchmark["Date"],
                      y=cumret*100, name="S&P 500"))
               
                st.plotly_chart(fig) 
                    
        
        
            
            df_order_modified["盈亏"] = df_order_modified["淨期权金_卖"] + df_order_modified["淨期权金_买"]
            option_pnl = sum(df_order_modified["盈亏"])
            總期权金收入 = 0
            
            col1, col2= st.columns([1,1])
            with col1:
                st.metric(
                    "總期权金回報(年化比率)",
                    f"{((1+return_per)**(365/period)-1)*100:,.2f}%")
        
            with col2:
                st.metric(
                    "期內回報",
                    f"{return_per*100:,.2f}%")
            
            st.markdown("---")
            col1, col2, col3= st.columns([1,1,1])
            with col1:
                st.metric(
                    "總期权金回報",
                    f"USD {option_pnl:,.2f}")
                st.metric(
                    "已平倉期权金回報",
                    f"USD {option_pnl_settled:,.2f}")
                st.metric(
                    "交易期(包含假日)",
                    f"{period:.0f}日")
            with col2:
                st.metric(
                    "最大回撤",
                    f"USD {max_dawndown:,.2f}")
                st.metric(
                    "平均盈利虧損",
                    f"盈利 +{reward_ratio:,.0f} : 虧損 {risk_ratio:,.0f}")
            with col3:
                st.metric(
                    "總手續費 (所有回報,比率均已計算手續費)",
                    f"USD {total_commission:,.2f}")
                st.metric(
                    "贏輸比例",
                    f"贏 {win_num:.0f} : 輸 {loss_num:.0f}")
               
            st.markdown("---")   
            st.header("倉位處理")    
            
            st.metric(
                "交易數(套)",
                f"{number_of_trade:.0f}")   
                
                
            col1, col2, col3, col4= st.columns([1,1,1,1])
            with col1:
                floating_order = len(df_order_modified[df_order_modified["交易種類"] == "未平倉"])
                st.metric(
                    "未平倉",
                    f"{floating_order:,.0f}")
        
            with col2:
                settled = len(df_order_modified[df_order_modified["交易種類"] == "平倉"])        
                st.metric(
                    "主動平倉",
                    f"{settled:,.0f}")
           
            with col3:
                expire = len(df_order_modified[df_order_modified["交易種類"] == "到期"])        
                st.metric(
                    "到期",
                    f"{expire:,.0f}")
            
            with col4:
                partial = len(df_order_modified[df_order_modified["交易種類"] == "分段平倉(到期/手動)"])        
                st.metric(
                    "分段平倉(主動/到期)",
                    f"{partial- len(duplicate_order_sell)}")   
                
        
            st.markdown("---")   
            st.header("單一交易")
            col1, col2, col3= st.columns([1,1,1])
            with col1:
                st.metric(
                    "盈利最高交易",
                    f"{best_trade:,.2f}")
        
            with col2:
                st.metric(
                    "虧損最大交易",
                    f"{worst_trade:,.2f}")
           
            with col3:
                st.metric(
                   "最長持倉日期 (日)",
                   f"{Longest_trade:.0f}")    
            st.markdown("---")      
            st.header("綜合持倉分析")
            with st.expander("点击展开 (期權標的(股票)個別回報)", expanded=False):
                st.bar_chart(option_result_by_stock)
            col1, col2= st.columns([1,1])
        
            with col1:
                st.header("10大交易期權標的(股票額 USD)")
                
                stock_value = df_order_modified.groupby("股票代碼")
                option_result_by_stock_volume = pd.DataFrame(stock_value.sum()['stock_value']).reset_index()
                option_result_by_stock_volume = option_result_by_stock_volume.sort_values(by="stock_value",ascending=False).head(10)
                fig = px.pie(option_result_by_stock_volume, values='stock_value', names="股票代碼")
                fig.update_traces(textposition='inside', textinfo='value+label',insidetextorientation='radial')
                st.plotly_chart(fig)
                
                st.header("10大交易期權標的(次數)")
                
                stock_value = df_order_modified.groupby("股票代碼")
                option_result_by_stock_count = pd.DataFrame(stock_value.count()['stock_value']).reset_index()
                option_result_by_stock_count = option_result_by_stock_count.sort_values(by="stock_value",ascending=False).head(10)
                fig = px.pie(option_result_by_stock_count, values='stock_value', names="股票代碼")
                fig.update_traces(textposition='inside', textinfo='value+label',insidetextorientation='radial')
                st.plotly_chart(fig)
                
            with col2:
                st.header("10大盈利最高期權標的(股票)")
                stock_ratio = option_result.groupby("股票代碼")
                st.bar_chart(option_result_by_stock.sort_values(by="盈亏",ascending=False).head(10))
                
                
                
                
        with tab2:
            col1, col2, col3= st.columns([1,1,1])
            df_floating = df_order_modified[df_order_modified["交易種類"] == "未平倉"]
            floating_stock_value = df_floating.groupby("股票代碼")
            floating_stock_value = pd.DataFrame(floating_stock_value.sum()['stock_value']).reset_index()
            floating_stock_value = floating_stock_value.sort_values(by="stock_value",ascending=False)
            
            
            with col1:
                st.metric(
                    "未平倉交易",
                    f"{floating_order:,.0f}")
        
            with col2:
                st.metric(
                    "未平倉期權(股票)總值",
                    f"USD {sum(floating_stock_value.stock_value):,.2f}")
           
            with col3:
                st.metric(
                   "資金/持倉倍數",
                   f"{(sum(floating_stock_value.stock_value)/fund_in_out_sum):.2f}x")    
        
            
            
            col1, col2= st.columns([1,1])
        
            with col1:
                st.header("未平倉期權標的(股票)")
                fig = px.pie(floating_stock_value, values='stock_value', names="股票代碼")
                fig.update_traces(textposition='inside', textinfo='value+label',insidetextorientation='radial')
                st.plotly_chart(fig)
                
            with col2:
                st.header("交易期權標的(股票)")        
                #check with live stock price
                df_floating["最後價格"] = 0
                for index,row in df_floating.iterrows():
                    price = yf.download(row.股票代碼)["Adj Close"][-1]
                    df_floating.at[index,"最後價格"] = price
                df_floating["距離履约价%"] = ((df_floating["最後價格"] - df_floating["履约价格"])/df_floating["最後價格"])*100
                df_floating["距離到期日"] = df_floating["到期日"].apply(lambda x: (x.date()-date.today()).days)
                #chart
                      
                fig = px.scatter(df_floating, x="距離到期日", y="距離履约价%",
        	         size="stock_value", color="股票代碼",hover_name="股票代碼", log_x=False, size_max=60)
                st.plotly_chart(fig)
        
            df_floating = df_floating[["日期_卖","股票代碼","认购/认沽_卖","数量_卖","手續費_卖","履约价格","最後價格","距離履约价%","到期日","距離到期日"]]
            st.dataframe(df_floating)
            
        
            
        
            
        with tab3:
            st.title(F"出入金總額(USD): {fund_in_out_sum:,.0f}")
            st.dataframe(fund_in_out)
        
        
            
        with tab4:   
            st.markdown(f"File Data: {length_all} rows")
            st.markdown(f"Option Transactions Data: {length_option_transaction} rows")   
            st.markdown(f"Others Data: {length_other} rows")            
            st.markdown("---")       
            col1, col2= st.columns([1,1])
            
            with col1:
                st.markdown("SELL")
                st.markdown(f"Sell data total: {length_sell_total} rows")
                st.markdown(f"Sell match buy data: {length_sell_match} rows")   
                st.markdown(f"Sell not match buy data: {length_sell_non_match} rows")
                st.markdown(f"Sell duplicate data: {len(duplicate_order_sell)} rows")     
                
        
            with col2:
                st.markdown("BUY")
                st.markdown(f"Buy Data total: {length_buy_total} rows")
                st.markdown(f"Buy match sell data: {length_buy_match} rows")   
                st.markdown(f"Buy not match sell data: {length_buy_non_match} rows")
                st.markdown(f"Buy duplicate data: {len(duplicate_order_buy)} rows") 
                
            st.markdown("Remark Sell + Buy - duplicate = total transactions")
    
