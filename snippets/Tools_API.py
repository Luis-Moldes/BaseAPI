from scipy import signal
import numpy.polynomial.polynomial as poly
import numpy as np
from scipy.optimize import curve_fit
import math
import pandas as pd

def rotate_angles_180(list, angle):

    list2=[]

    for item in list:
        ang=item+angle
        if ang>180:
            ang-=360
        if ang<-180:
            ang+=360
        list2.append(ang)

    return list2


def angles_stats(angles,func,twa=False):

    x=[]
    y=[]

    for i in angles:
        x.append(math.cos(i * math.pi / 180))
        y.append(math.sin(i * math.pi / 180))

    if func=='Mean':
        x = np.mean(x)
        y = np.mean(y)
        mean = math.atan2(y, x) * 180 / math.pi
    elif func=='Median':
        x = np.median(x)
        y = np.median(y)
        mean = math.atan2(y, x) * 180 / math.pi
    elif func=='Stdd':
        x = np.mean(x)
        y = np.mean(y)
        mean=math.sqrt(-math.log(y * y + x * x))

    if func != 'Stdd':
        if twa:
            if mean < -180:
                mean = mean + 360
            elif mean > 180:
                mean = mean - 360
        else:
            if mean < 0:
                mean = mean + 360
            elif mean > 360:
                mean = mean - 360

    return mean


def lowpass(data, cutout):
    b, a = signal.butter(5, cutout, 'low')
    zi = signal.lfilter_zi(b, a)
    z, _= signal.lfilter(b, a, data, zi=zi*data[0])
    z2, _ = signal.lfilter(b, a, z, zi=zi*z[0])
    y = signal.filtfilt(b, a, data)
    return y


def outliers_scan(data):
    u = np.mean(data)
    s = np.std(data)

    data_processed = []
    data_processed.append(data[0])

    for i in range(1, len(data)):
        if u-2*s < data[i] < u+3*s:
            data_processed.append(data[i])
        elif data[i] > u+3*s:
            data_processed.append(data_processed[i-1])
        else:
            data_processed.append(data[i])

    return data_processed


def latlon_to_metres(lat1, lat2, lon1, lon2):

    r_earth = 6371000   # Radius of the earth in meters

    lat1 = lat1 * math.pi / 180
    lat2 = lat2 * math.pi / 180
    lon1 = lon1 * math.pi / 180
    lon2 = lon2 * math.pi / 180

    a = math.sin((lat2-lat1)/2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = r_earth * c

    return d


def latlon_course(lat1, lat2, lon1, lon2):

    lat1 = lat1 * math.pi/180
    lat2 = lat2 * math.pi / 180
    lon1 = lon1 * math.pi / 180
    lon2 = lon2 * math.pi / 180

    x = math.cos(lat2) * math.sin(lon2 - lon1)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    beta = math.atan2(x, y)*180/math.pi

    return beta


def latlon_course360(lat1, lat2, lon1, lon2):

    lat1 = lat1 * math.pi/180
    lat2 = lat2 * math.pi / 180
    lon1 = lon1 * math.pi / 180
    lon2 = lon2 * math.pi / 180

    x = math.cos(lat2) * math.sin(lon2 - lon1)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    beta = math.atan2(x, y)*180/math.pi

    if beta < 0:
        beta = beta + 360
    elif beta > 360:
        beta = beta - 360

    return beta


def magneto_calib(data, x):

    output_data = []

    for i in range(0, len(data)):
        output_data.append(data[i] + x)

    return output_data


def TimeDelta(time1, time2):

    dt = pd.Timedelta(time2 - time1).microseconds*0.000001 + pd.Timedelta(time2 - time1).seconds

    return dt


def fit(indexes, TWD_list, time, polynomial, exp, log):

    # print('degree = ', poly)
    twdlist = TWD_list.tolist()
    indexes = indexes.tolist()

    indexes = list(filter(None, indexes))
    twdlist = list(filter(None, twdlist))

    # print('length of the twd list: ', len(twdlist))
    # print('length of the indexes list: ', len(indexes))

    index_new = np.linspace(0, len(time) - 1, num=len(time), dtype=int)
    # print('new indexes list: ', len(index_new), index_new)

    if polynomial is not None:

        coefs = poly.polyfit(indexes, twdlist, polynomial)
        # print('coefs = ', coefs)
        TWD_fit = poly.polyval(index_new, coefs)

    elif exp is not None:

        def exp_fun(x, c0, c1, c2, c3):
            return c0+c1*x-c2*np.exp(-c3*x)

        c, cov = curve_fit(exp_fun, indexes, twdlist)

        TWD_fit = exp_fun(index_new, c[0], c[1], c[2], c[3])

    elif log is not None:

        def log_fun(x, c0, c1, c2, c3):
            return c0 + c1 * x - c2 * np.log(-c3 * x)

        c, cov = curve_fit(log_fun, indexes, twdlist)

        TWD_fit = log_fun(index_new, c[0], c[1], c[2], c[3])

    return TWD_fit


def adjust_length(lists, length):

    for li in lists:

        if len(li) > length:

            lists = adjust_length((lists, len(li)))

        elif len(li) <= length:

            size_dif = abs(len(li) - length)
            li.extend(['']*size_dif)

    return lists


def m_s_to_knots(speed_df):

    speed_df = [s/0.51444 for s in speed_df]

    return speed_df


def merge_logs(logs, dt):
    log_0 = logs[0]
    log_1 = logs[1]

    end_time_first = log_0.loggingTime[-1]
    start_time_second = log_1.loggingTime[0]

    time_jump = TimeDelta(end_time_first, start_time_second)
    fill_indexes = time_jump / dt

    if time_jump > 1:
        fill_time_interval = pd.date_range(start=end_time_first + pd.Timedelta(milliseconds=1000*dt),
                                           end=start_time_second - pd.Timedelta(milliseconds=1000*dt), freq=str(dt)+'S')
        temp_df = pd.DataFrame(columns=log_0.columns, index=fill_time_interval)
        temp_df.loggingTime = fill_time_interval

        for col in [col_list for col_list in temp_df.columns if col_list != 'loggingTime']:

            evolution = np.linspace(log_0[col][-1], log_1[col][0], fill_indexes)
            evolution = np.delete(evolution, 0)
            temp_df[col] = evolution

        temp_df['locationSpeed'] = [-1]*len(temp_df.loggingTime)

    frame_1 = [log_0, temp_df, log_1]
    log = pd.concat(frame_1, sort=False)

    return log
