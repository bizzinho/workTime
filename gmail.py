# -*- coding: utf-8 -*-
"""
Created on Tue Oct  9 15:48:23 2018

@author: dochsenb
"""

import googleapiclient as gapi
from oauth2client import file, client, tools
from httplib2 import Http
import pdb
import base64
from dateutil import parser
import datetime as dt
import os
import pandas as pd
import numpy as np
import seaborn as sns

def intersectingHours(timeWindow1_start,timeWindow1_end,timeWindow2_start,timeWindow2_end):
    laterStart = np.max([timeWindow1_start,timeWindow2_start])
    earlierEnd = np.min([timeWindow1_end,timeWindow2_end])
    
    return (earlierEnd-laterStart).days*24

def GetDate(service,msg_id, user_id = 'me',stringIt = False):
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()  
    
    for item in message['payload']['headers']:
        if item['name'] == 'Date':
           date = parser.parse(item['value'])
           if stringIt == True:
               date = date.strftime("%d%b%Y_%H%M")
           
    return date

def GetAttachments(service, msg_id, store_dir = './data/', user_id = 'me'):
    datestr = GetDate(service = service,msg_id = msg_id,user_id = user_id,stringIt = True)

    message = service.users().messages().get(userId=user_id, id=msg_id).execute()  
           
    if 'parts' in message['payload']: 
        parts = message['payload']['parts']
    else:
        parts = [message['payload']]

    for part in parts:
        
        try:
            if part['filename'] == 'data.csv':
                
                if 'data' in part['body']:
                    locdata=part['body']['data']
                else:
                    att_id=part['body']['attachmentId']
                    att=service.users().messages().attachments().get(userId=user_id, messageId=msg_id,id=att_id).execute()
                    locdata=att['data']
                    
                file_data = base64.urlsafe_b64decode(locdata.encode('UTF-8'))
    #            pdb.set_trace()
                path = ''.join([store_dir, part['filename'].split('.')[0],'_',datestr,'.csv'])# +dt.datetime.now().strftime("%Y%m%d")
                
                f = open(path, 'wb')
                f.write(file_data)
                f.close()
        except:
            pdb.set_trace()

dates = []
for myFile in os.listdir('./data/'):
    date = myFile.split('data_')[1]
    date = date.split('.')[0]
    dates.append(dt.datetime.strptime(date,'%d%b%Y_%H%M'))

lastDate = np.max(dates)    

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
store = file.Storage('token.json')
creds = store.get()

GMAIL = gapi.discovery.build('gmail', 'v1', http=creds.authorize(Http()))

messages = GMAIL.users().messages().list(userId = 'me',q='from:dave.ochsenbein@gmail.com AND subject:My Work Clock AND after:'+lastDate.strftime('%Y/%m/%d')).execute()

msgIDs = [message['id'] for message in messages['messages']]

for myID in msgIDs:
    GetAttachments(GMAIL,msg_id = myID)

msg_dates = [GetDate(GMAIL,msg_id = myID) for myID in msgIDs]
latest_msgDate, latestI = np.max(msg_dates), np.argmax(msg_dates)

holidays = pd.read_excel('./holidays.xlsx')
        
X = pd.read_csv('./data/data_'+latest_msgDate.strftime("%d%b%Y_%H%M")+'.csv')
    
#X = pd.DataFrame()
#for myFile in os.listdir('./data/'):
#    df = pd.read_csv('./data/'+myFile)
#    X = X.append(df)
    #X.drop_duplicates(inplace=True)
    

X.drop(['Time (seconds)','Time (hours)','Income','Job'],axis=1,inplace=True)

X['Start time'] = pd.core.tools.datetimes.to_datetime(X['Start time'])
X['End time'] = pd.core.tools.datetimes.to_datetime(X['End time'])  
  
X['Start day'] = X['Start time'].apply(lambda x: x.date())
X['End day'] = X['End time'].apply(lambda x: x.date())

# for periods that cross midnight we split them in two for easier handling later
for ind in X[X['Start day'] != X['End day']].index:
    df = pd.DataFrame(columns = X.columns)
    df = df.append(X.loc[ind],ignore_index=True)
    df = df.append(X.loc[ind],ignore_index=True)
    
    
    df.loc[0,'End time'] = dt.datetime.combine(df.loc[0,'Start day'],dt.time(hour = 23,minute=59))
    df.loc[0,'End day'] = df.loc[0,'Start day'] 
    
    df.loc[1,'Start time'] = dt.datetime.combine(df.loc[1,'End day'],dt.time(hour = 0,minute=0))
    df.loc[1,'Start day'] = df.loc[1,'End day'] 
    
    X = X.drop(ind)
    X = X.append(df)

X['Duration'] = (X['End time']-X['Start time']) / pd.Timedelta(hours = 1)

Xwork = X[X['Description'] != 'Travel']

startHour = Xwork.groupby('Start day')['Start time'].min().dt.hour + Xwork.groupby('Start day')['Start time'].min().dt.minute / 60
endHour = Xwork.groupby('End day')['End time'].max().dt.hour + Xwork.groupby('End day')['End time'].max().dt.minute / 60
sns.boxplot(data = [startHour,endHour])

startDate = X['Start day'].min() - dt.timedelta(days = X['Start day'].min().weekday()) # we analyze weeks and start with the Monday of the week with the first record
endDate = X['End day'].max()

rng = pd.period_range(start=startDate,freq='W',end=endDate)

weekHours = []
for period in rng:
    Xperiod = Xwork[(period.start_time <= Xwork['Start time']) and (Xwork['End time'] <= period.end_time)]
    holidayHours = holidays[(period.start_time <= holidays['Date']) and (holidays['Date'] <= period.end_time)]
    weekHours.append(Xperiod['Duration'].sum())


# weekend working
# average hours per week
# histogram of hours per day
# day start time histogram; split from travel items
