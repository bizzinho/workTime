# -*- coding: utf-8 -*-
"""
Created on Sat Jun 13 13:49:11 2020

@author: dochsenb
"""

import pandas as pd

df = pd.read_excel("data_13Jun2020.xlsx")

df['Description'] = df.Description.replace('Normal','Schaffhausen')
df['Description'] = df.Description.replace('Beerse','Belgium')

df.drop(['Income','Job'], axis = 1, inplace = True)

df['Start Date'] = df['Start time'].dt.date
df2 = pd.DataFrame(df[df.Description != "Travel"].groupby('Start Date')['Time (hours)'].sum())
df2.columns = ["WorkPerDay"]

writer = pd.ExcelWriter('myWorkingHours.xlsx')

df.to_excel(writer, sheet_name= "original")
df2.to_excel(writer, sheet_name= "perDate")

writer.save()