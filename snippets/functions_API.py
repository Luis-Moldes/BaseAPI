import math
import statistics as stat
import pandas as pd
import numpy as np
import gpxpy
import os
from scipy import stats
import matplotlib.pyplot as plt
import datetime
from snippets.Tools_API import lowpass, latlon_to_metres, latlon_course, magneto_calib, TimeDelta, latlon_course360, \
    angles_stats, rotate_angles_180
import warnings
import xml.etree.ElementTree as ET
from collections import defaultdict
from scipy.stats import circstd


warnings.filterwarnings("ignore", category=DeprecationWarning)


def read_configs(path):
    fileObj = open(path)
    output = {}

    for line in fileObj:
        key_value = line.split('=')
        if len(key_value) == 2:
            output[key_value[0]] = key_value[1].rstrip()

    return output


def read_parameters(fileName):
    fileObj = open(fileName)
    params = {}

    """ Reading the file"""

    for line in fileObj:


        line = line.strip()
        key_value = line.split('=')
        if len(key_value) == 2:
            params[key_value[0].strip()] = key_value[1].strip()

    """ Convert the parameters into their type"""

    # BOOLEAN PARAMETERS ...
    def str_to_bool(s):
        if s == 'True':
            t = True
            return t
        elif s == 'False':
            t = False
            return t

    Bool_list = ['create_plots', 'create_scatter', 'wind_man_cal', 'show_phases',
                 'wind_auto_cal', 'phase_creation', 'TWD_is_present', 'show_tack_gybe', 'phases_only_portions', 'race_mode',
                 'Read_Event_Time', 'event_creation', 'export_creation', 'csv_creation', 'no_man_legs']

    for boo in Bool_list:
        params[boo] = str_to_bool(params[boo])


    Fl_list = ['dt','lowpass_freq','mag_variation','tacking_angle','maneuver_angle','time_1_hdg_before','time_2_hdg_before',
               'time_1_hdg_after','time_2_hdg_after','time_hdgmax','time_1_TWA','time_2_TWA','up_down_twa_limit',
               'man_wand_to_avoid_after','man_wand_to_avoid_before','phase_length','std_twa_limit','speed_median_min',
               'man_time_before','man_time_after_2','man_time_after_1','TWD_of_the_day','TWS_of_the_day',
               'Temperature_of_the_day','Pressure_of_the_day','Upwind_Reach_Angle','Downwind_Reach_Angle',
               'Minimum_Leg_Time','Race_Turn','Shift_Step_1','Shift_Step_2','Phase_Speed_Margin']

    for boo in Fl_list:
        params[boo] = float(params[boo])

    Int_list = ['SD_Time','Man_Time','Exp_Dec']

    for boo in Int_list:
        params[boo] = int(params[boo])

    # DateTime variables ...
    params['t_phase_start'] = pd.to_datetime(params['t_phase_start'])
    params['t_phase_stop'] = pd.to_datetime(params['t_phase_stop'])

    return params


def format_log(log_raw, config, time_shift):
    if config == 'SENSOR LOG':

        log_raw.index = log_raw.index.map(lambda x: x + pd.Timedelta(time_shift, 'h'))

        drop_cols = ['motionRotationRateX(rad/s)', 'motionRotationRateY(rad/s)', 'motionRotationRateZ(rad/s)',
                     'motionUserAccelerationX(G)', 'motionUserAccelerationY(G)', 'motionUserAccelerationZ(G)',
                     'motionAttitudeReferenceFrame(txt)', 'motionQuaternionX(R)', 'motionQuaternionY(R)',
                     'motionQuaternionZ(R)', 'motionQuaternionW(R)', 'motionGravityX(G)', 'motionGravityY(G)',
                     'motionGravityZ(G)', 'motionMagneticFieldX(T)', 'motionMagneticFieldY(T)',
                     'motionMagneticFieldZ(T)',
                     'motionMagneticFieldCalibrationAccuracy(Z)', 'activityTimestamp_sinceReboot(s)', 'activity(txt)',
                     'activityActivityConfidence(Z)', 'activityActivityStartDate(txt)', 'pedometerStartDate(txt)',
                     'pedometerNumberofSteps(N)', 'pedometerAverageActivePace(s/m)', 'pedometerCurrentPace(s/m)',
                     'pedometerCurrentCadence(steps/s)', 'pedometerDistance(m)', 'pedometerFloorAscended(N)',
                     'pedometerFloorDescended(N)', 'pedometerEndDate(txt)', 'altimeterTimestamp_sinceReboot(s)',
                     'altimeterReset(bool)', 'altimeterRelativeAltitude(m)', 'altimeterPressure(kPa)', 'IP_en0(txt)',
                     'IP_pdp_ip0(txt)', 'deviceOrientation(Z)', 'batteryState(R)', 'batteryLevel(Z)',
                     'avAudioRecorderPeakPower(dB)',
                     'avAudioRecorderAveragePower(dB)', 'label(N)', 'motionTimestamp_sinceReboot(s)',
                     'magnetometerTimestamp_sinceReboot(s)',
                     'gyroTimestamp_sinceReboot(s)', 'accelerometerTimestamp_sinceReboot(s)',
                     'locationHeadingAccuracy(°)',
                     'locationVerticalAccuracy(m)', 'locationHorizontalAccuracy(m)', 'locationFloor(Z)',
                     'locationHeadingTimestamp_since1970(s)',
                     'locationHeadingX(T)', 'locationHeadingY(T)', 'locationHeadingZ(T)', 'loggingSample(N)',
                     'identifierForVendor(txt)',
                     'deviceID(txt)', 'locationTimestamp_since1970(s)']

        for name in drop_cols:
            del log_raw[name]

        log = log_raw.resample('S').mean()

        time = log.index.values
        log.insert(loc=0, column='Date_Time', value=time)
        log.reset_index(drop=True, inplace=True)

        new_col_names = ["Date_Time", "Latitude", "Longitude", "Altitude", "SOG_mps", "COG", "True_HDG", "Mag_HDG",
                         "Acc_X", "Acc_Y", "Acc_Z", "Gyro_X", "Gyro_Y", "Gyro_Z", "Mag_X", "Mag_Y", "Mag_Z", "Yaw",
                         "Roll", "Pitch"]

        log.columns = new_col_names
        log_raw = log

    if config == 'GPX + EasyWind':

        drop_cols = ['only_time', 'latitude', 'longitude', 'heading', 'SOG', 'COG', 'pitch', 'roll']

        for name in drop_cols:
            del log_raw[name]

        new_col_names = ['Date_Time', 'Latitude', 'Longitude', 'Altitude', 'TWD', 'TWS', 'Temperature', 'Pressure']

        log_raw.columns = new_col_names

    return log_raw


def write_parameters(params, filename):

    file = open(filename, 'w')
    # Bool_list = ['create_plots', 'create_scatter', 'wind_man_cal', 'show_phases',
    #              'wind_auto_cal', 'phase_creation', 'TWD_is_present', 'show_tack_gybe', 'phases_only_portions', 'race_mode',
    #              'Read_Event_Time', 'event_creation', 'export_creation']

    # Booleans ...

    for p in params:
        file.writelines(p + ' = ' + str(params[p]) + '\n')

    # file.writelines('create_plots = ' + str(params['create_plots']) + '\n')
    # file.writelines('create_scatter = ' + str(params['create_scatter']) + '\n')
    # file.writelines('wind_man_cal = ' + str(params['wind_man_cal']) + '\n')
    # file.writelines('show_phases = ' + str(params['show_phases']) + '\n')
    # file.writelines('wind_auto_cal = ' + str(params['wind_auto_cal']) + '\n')
    # file.writelines('phase_creation = ' + str(params['phase_creation']) + '\n')
    # file.writelines('TWD_is_present = ' + str(params['TWD_is_present']) + '\n')
    # file.writelines('show_tack_gybe = ' + str(params['show_tack_gybe']) + '\n')
    # file.writelines('phases_only_portions = ' + str(params['phases_only_portions']) + '\n')
    # file.writelines('race_mode = ' + str(params['race_mode']) + '\n')
    #
    # file.writelines( '\n')
    #
    # # Constants ...
    #
    # file.writelines('dt = '+ str(params['dt'])+'\n')
    # file.writelines('lowpass_freq = '+ str(params['lowpass_freq'])+'\n')
    # file.writelines('mag_variation = '+ str(params['mag_variation'])+'\n')
    # file.writelines('tacking_angle = ' + str(params['tacking_angle']) + '\n')
    # file.writelines('maneuver_angle = ' + str(params['maneuver_angle']) + '\n')
    # file.writelines('time_1_hdg_before = ' + str(params['time_1_hdg_before']) + '\n')
    # file.writelines('time_2_hdg_before = ' + str(params['time_2_hdg_before']) + '\n')
    # file.writelines('time_1_hdg_after = ' + str(params['time_1_hdg_after']) + '\n')
    # file.writelines('time_2_hdg_after = ' + str(params['time_2_hdg_after']) + '\n')
    # file.writelines('time_hdgmax = ' + str(params['time_hdgmax']) + '\n')
    # file.writelines('time_1_TWA = ' + str(params['time_1_TWA']) + '\n')
    # file.writelines('time_2_TWA = ' + str(params['time_2_TWA']) + '\n')
    # file.writelines('up_down_twa_limit = ' + str(params['up_down_twa_limit']) + '\n')
    # file.writelines('man_wand_to_avoid_before = ' + str(params['man_wand_to_avoid_before']) + '\n')
    # file.writelines('man_wand_to_avoid_after = ' + str(params['man_wand_to_avoid_after']) + '\n')
    # file.writelines('phase_length = ' + str(params['phase_length']) + '\n')
    # file.writelines('std_twa_limit = ' + str(params['std_twa_limit']) + '\n')
    # file.writelines('speed_median_min = ' + str(params['speed_median_min']) + '\n')
    # file.writelines('man_time_before = ' + str(params['man_time_before']) + '\n')
    # file.writelines('man_time_after_2 = ' + str(params['man_time_after_2']) + '\n')
    # file.writelines('man_time_after_1 = ' + str(params['man_time_after_1']) + '\n')
    # file.writelines('TWD_of_the_day = ' + str(params['TWD_of_the_day']) + '\n')
    # file.writelines('TWS_of_the_day = ' + str(params['TWS_of_the_day']) + '\n')
    # file.writelines('Temperature_of_the_day = ' + str(params['Temperature_of_the_day']) + '\n')
    # file.writelines('Pressure_of_the_day = ' + str(params['Pressure_of_the_day']) + '\n')
    # file.writelines('Upwind_Reach_Angle = ' + str(params['Upwind_Reach_Angle']) + '\n')
    # file.writelines('Downwind_Reach_Angle = ' + str(params['Downwind_Reach_Angle']) + '\n')
    # file.writelines('Minimum_Leg_Time = ' + str(params['Minimum_Leg_Time']) + '\n')
    # file.writelines('Race_Turn = ' + str(params['Race_Turn']) + '\n')
    # file.writelines('Shift_Step_1 = ' + str(params['Shift_Step_1']) + '\n')
    # file.writelines('Shift_Step_2 = ' + str(params['Shift_Step_2']) + '\n')
    # file.writelines('Phase_Speed_Margin = ' + str(params['Phase_Speed_Margin']) + '\n')
    #
    # file.writelines('\n')
    # # # DateTime variables ...
    # #
    # file.writelines('t_phase_start = ' + str(params['t_phase_start']) + '\n')
    # file.writelines('t_phase_stop = ' + str(params['t_phase_stop']) + '\n')


    file.close()


def gpx_to_csv(gpx_file):
    csv_file_name = gpx_file.strip('.gpx')
    csv_file_name = csv_file_name.replace('Input', 'Outputs')
    csv_file = open(csv_file_name + '.csv', 'w')
    csv_file.writelines(
        'Date_Time,only_time,Latitude,Longitude,Elevation\n')
    rd = []

    points2 = list()
    with open(gpx_file, 'r') as gpxfile:
        gpx = gpxpy.parse(gpxfile)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    dict = {'Timestamp': point.time,
                            'Latitude': point.latitude,
                            'Longitude': point.longitude,
                            'Elevation': point.elevation
                            }

                    printline = str(point.time.year) + '-' + str(point.time.month) + '-' + str(point.time.day) + ' ' + \
                                str(point.time.hour) + ':' + str(point.time.minute) + ':' + str(point.time.second) + \
                                ',' + str(point.time.hour) + ':' + str(point.time.minute) + ':' + str(
                        point.time.second) + \
                                ',' + str(point.latitude) + \
                                ',' + str(point.longitude) + \
                                ',' + str(point.elevation)

                    rd.append(printline)
                    points2.append(dict)

    for i in range(0, len(rd)):
        csv_file.write(rd[i] + '\n')

    csv_file.close()

    return csv_file.name


def synchronize_logs(ref_log, log_2):
    log_2 = log_2.iloc[::-1]

    new_log = pd.merge_asof(ref_log, log_2, on='Date_Time', suffixes=('','_ew'))

    return new_log


def calculate_roll(accx, accy, accz, pitch, gyroY, dt, time, cutout_lowpass_freq):
    # Filtering the data from the accelerometer
    AccX_filtered = lowpass(accx, cutout_lowpass_freq)
    AccY_filtered = lowpass(accy, cutout_lowpass_freq)
    AccZ_filtered = lowpass(accz, cutout_lowpass_freq)

    # Calculating Roll motion from the accelerometer data
    roll_acc = []

    for i in range(0, len(time)):
        roll_acc.append(math.atan(-AccX_filtered[i] / (AccY_filtered[i] * math.sin(math.radians(pitch[i]))
                                                       + AccZ_filtered[i] * math.cos(
                    math.radians(pitch[i])))) * 180 / math.pi)

    """ COMPLEMENTARY FILTER IF WANTED

    # Calculating Roll and Pitch motion from the gyroscope data
    roll_gyro = []

    roll_gyro.append(roll_acc[0])

    for i in range(1, len(log.loggingTime)):
        roll_gyro.append(roll_gyro[i-1] + log.gyroY[i-1]*dt*180/math.pi)

    roll = []

    # applying complementary filter
    for i in range(0, len(log.loggingTime)):
        roll.append(0 * roll_gyro[i] + 0.8 * roll_acc[i])
    """

    mn = stat.median(roll_acc)
    roll_acc = [x - mn for x in roll_acc]
    return roll_acc


def calculate_pitch(accy, accz, gyroX, dt, time, cutout_lowpass_freq):
    # Filtering the data from the accelerometer
    AccY_filtered = lowpass(accy, cutout_lowpass_freq)
    AccZ_filtered = lowpass(accz, cutout_lowpass_freq)

    # Calculating Roll motion from the accelerometer data
    pitch_acc = []

    for i in range(0, len(time)):
        pitch_acc.append(180 + math.atan2(AccY_filtered[i], AccZ_filtered[i]) * 180 / math.pi)
        if pitch_acc[i] > 180:
            pitch_acc[i] = pitch_acc[i] - 360

    """ COMPLEMENTARY FILTER IF WANTED

    # Calculating Roll and Pitch motion from the gyroscope data
    pitch_gyro = []

    pitch_gyro.append(pitch_acc[0])


    for i in range(1, len(time)):
        pitch_gyro.append(pitch_gyro[i-1] + (log.gyroX[i-1])*dt*180/math.pi)

    pitch = []

    # applying complementary filter
    for i in range(0, len(time)):
        pitch.append(0.2 * pitch_gyro[i] + 0.8 * pitch_acc[i])
"""

    return pitch_acc


def calculate_yaw(accy, accz, time, cutout_lowpass_freq):
    # Filtering the data from the accelerometer
    AccY_filtered = lowpass(accy, cutout_lowpass_freq)
    AccZ_filtered = lowpass(accz, cutout_lowpass_freq)

    # Calculating Yaw motion from the accelerometer data
    yaw_acc = []

    for i in range(0, len(time)):
        yaw_acc.append(math.atan2(AccZ_filtered[i], (
            math.sqrt(AccY_filtered[i] * AccY_filtered[i] + AccZ_filtered[i] * AccZ_filtered[i]))) * 180 / math.pi)

    return yaw_acc


def calculate_heading(magx, magy, magz, roll, pitch, time, mag_variation, cutout_lowpass_freq):
    declination = mag_variation

    # Calculating the magnetic heading with tilt-correction and Hard Iron effects
    Bfx = []
    Bfy = []
    Mag_Heading = []
    Mag_Heading_corr = []

    magx = magneto_calib(magx, -20)
    magy = magneto_calib(magy, 5)

    # corrected heading
    for i in range(0, len(time)):
        Bfx.append(magy[i] * math.cos(math.radians(pitch[i])) + magx[i] * math.sin(math.radians(pitch[i]))
                   * math.sin(math.radians(roll[i])) + magz[i] * math.sin(math.radians(pitch[i]))
                   * math.cos(math.radians(roll[i])))
        Bfy.append(magx[i] * math.cos(math.radians(roll[i])) + magz[i] * math.sin(math.radians(roll[i])))

        Mag_Heading_corr.append(math.atan2(-Bfy[i], Bfx[i]) * 180 / math.pi)

        if Mag_Heading_corr[i] < 0:
            Mag_Heading_corr[i] = Mag_Heading_corr[i] + 360
        if Mag_Heading_corr[i] >= 360:
            Mag_Heading_corr[i] = Mag_Heading_corr[i] - 360

    Mag_Heading_corr = lowpass(Mag_Heading_corr, cutout_lowpass_freq)

    # heading calculated with simple formula
    for i in range(0, len(time)):
        if magy[i] > 0:
            Mag_Heading.append(90 - math.atan(magx[i] / magy[i]) * 180 / math.pi)
        elif magy[i] < 0:
            Mag_Heading.append(270 - math.atan(magx[i] / magy[i]) * 180 / math.pi)
        elif magy[i] == 0 and magx[i] > 0:
            Mag_Heading.append(0)
        elif magy[i] == 0 and magx[i] < 0:
            Mag_Heading.append(180)

    # Calculating the true heading
    True_Heading = [x + declination for x in Mag_Heading_corr]

    for i in range(0, len(time)):
        if True_Heading[i] > 360:
            True_Heading[i] = True_Heading[i] - 360

    return Mag_Heading_corr, True_Heading, Mag_Heading


########################################################################################################################


def coord_interpol(lat, lon, time):
    Ilat = []
    Ilon = []

    for i in range(0, (len(time) - 1)):

        if (i < (len(time)-1) and lon[i] == lon[i + 1] and lat[i] == lat[i + 1]) and (
                lon[i] != lon[i - 1] or lat[i] != lat[i - 1]):  # First repetition with respect to the next measurement

            index = i
            reps = 0

            while lon[index] == lon[index + 1] and lat[index] == lat[
                index + 1] and index<(len(time)-1):  # Check for how many more measurements that goes on
                reps += 1
                index += 1

            for j in range(1,
                           reps + 1):  # You complete the following values with the mean between the last unrepeated value and THE LAST REPEATED VALUE (as seen in Sergi_13-05-19)
                Ilat.append(lat[i - 1] + j * (lat[i + reps] - lat[i - 1]) / (reps + 1))
                Ilon.append(lon[i - 1] + j * (lon[i + reps] - lon[i - 1]) / (reps + 1))

            Ilat.append(lat[i + reps])  # Add the last value aswell, as to make the next steps easier
            Ilon.append(lon[i + reps])

        elif i > 0 and lon[i] == lon[i - 1] and lat[i] == lat[
            i - 1]:  # do nothing if it repeats itself with respect to the previous value: that has already been taken care of
            pass

        else:
            Ilat.append(lat[i])
            Ilon.append(lon[i])

    # The program above will only add the last value if its a repetition. If thats not the case:

    if len(Ilat) < len(time):
        Ilat.append(lat[len(time) - 1])
        Ilon.append(lon[len(time) - 1])

    return Ilat, Ilon


def coord_interpol_reverse(lat, lon, time):
    Ilat = []
    Ilon = []

    for i in range(0, (len(time) - 1)):

        if (i < (len(time)-1) and lon[i] == lon[i + 1] and lat[i] == lat[i + 1]) and (
                lon[i] != lon[i - 1] or lat[i] != lat[i - 1]):  # First repetition with respect to the next measurement

            index = i
            reps = 0

            while lon[index] == lon[index + 1] and lat[index] == lat[
                index + 1] and index<(len(time)-1):  # Check for how many more measurements that goes on
                reps += 1
                index += 1

            Ilat.append(lat[i])  # Add the last value aswell, as to make the next steps easier
            Ilon.append(lon[i])

            for j in range(1,
                           reps + 1):  # You complete the following values with the mean between the last unrepeated value and THE LAST REPEATED VALUE (as seen in Sergi_13-05-19)
                Ilat.append(lat[i] + j * (lat[i + reps+1] - lat[i]) / (reps + 1))
                Ilon.append(lon[i] + j * (lon[i + reps+1] - lon[i]) / (reps + 1))

        elif i > 0 and lon[i] == lon[i - 1] and lat[i] == lat[
            i - 1]:  # do nothing if it repeats itself with respect to the previous value: that has already been taken care of
            pass

        else:
            Ilat.append(lat[i])
            Ilon.append(lon[i])

    # The program above will only add the last value if its a repetition. If thats not the case:

    if len(Ilat) < len(time):
        Ilat.append(lat[len(time) - 1])
        Ilon.append(lon[len(time) - 1])

    return Ilat, Ilon


def time_interpol(log, dt):  # For now, the program will first transform all the date into a dt=1, for later removing values.
                            # OJO: is not flexible, if the log has more fields you cannot reduce the timestep

    time=log.Date_Time

    Tlat = log.Latitude.tolist()
    Tlon = log.Longitude.tolist()
    Talt= log.Altitude.tolist()
    Ttwd = log.TWD.tolist()
    Ttws = log.TWS.tolist()
    Ttemp = log.Temperature.tolist()
    Tpress= log.Pressure.tolist()

    added = 0
    dt=int(dt)

    for i in range(0, (len(time) - 1)):

        a = time[i + 1] - time[i]

        if a.seconds > dt:
            missing = int(a.seconds - dt)
            Tlat = Tlat[:(i + 1 + added)] + (log.Latitude[i] + pd.Series(range(1, (missing + 1))) *
                    (log.Latitude[i + 1] - log.Latitude[i]) / (missing + 1)).tolist() + Tlat[(i + 1 + added):]
            Tlon = Tlon[:(i + 1 + added)]+ (log.Longitude[i] + pd.Series(range(1, (missing + 1))) *
                    (log.Longitude[i + 1] - log.Longitude[i]) / (missing + 1)).tolist() + Tlon[(i + 1 + added):]
            Talt = Talt[:(i + 1 + added)]+ (log.Altitude[i] + pd.Series(range(1, (missing + 1))) *
                    (log.Altitude[i + 1] - log.Altitude[i]) / (missing + 1)).tolist() + Talt[(i + 1 + added):]
            Ttwd = Ttwd[:(i + 1 + added)] + (log.TWD[i] + pd.Series(range(1, (missing + 1))) *
                    (log.TWD[i + 1] - log.TWD[i]) / (missing + 1)).tolist() + Ttwd[(i + 1 + added):]
            Ttws = Ttws[:(i + 1 + added)] + (log.TWS[i] + pd.Series(range(1, (missing + 1))) *
                    (log.TWS[i + 1] - log.TWS[i]) / (missing + 1)).tolist() + Ttws[(i + 1 + added):]
            Ttemp = Ttemp[:(i + 1 + added)] + ( log.Temperature[i] + pd.Series(range(1, (missing + 1))) *
                    (log.Temperature[i + 1] - log.Temperature[i]) / (missing + 1)).tolist() + Ttemp[(i + 1 + added):]
            Tpress = Tpress[:(i + 1 + added)] + (log.Pressure[i] + pd.Series(range(1, (missing + 1))) *
                    (log.Pressure[i + 1] - log.Pressure[i]) / (missing + 1)).tolist() + Tpress[(i + 1 + added):]

            added = added + missing

    intlog=pd.DataFrame()

    intlog['Date_Time']= pd.date_range(start=time[0], end=time[len(time) - 1], freq=(str(int(dt))+'s'))
    intlog['Latitude'] = pd.Series(Tlat[::dt])
    intlog['Longitude'] =pd.Series(Tlon[::dt])
    intlog['Altitude'] =pd.Series(Talt[::dt])
    intlog['TWD'] =pd.Series(Ttwd[::dt])
    intlog['TWS'] =pd.Series(Ttws[::dt])
    intlog['Temperature'] =pd.Series(Ttemp[::dt])
    intlog['Pressure'] =pd.Series(Tpress[::dt])


    return intlog


def csv_interpol(log):
    cols = log.columns

    for i in range(0, (len(log) - 1)):

        if np.isnan(log[cols[2]][i]):  # First repetition with respect to the next measurement

            index = i
            reps = 0

            while np.isnan(log[cols[2]][index]):  # Check for how many more measurements that goes on
                reps = reps + 1
                index = index + 1

            for col in cols[1:-1]:  # You complete the following values with the mean between the last unrepeated value and THE LAST REPEATED VALUE (as seen in Sergi_13-05-19)
                log[col][i:(index)]=log[col][i-1]+pd.Series(range(1,reps+1))*(log[col][index] - log[col][i-1]) / (reps + 1)

            i=i+reps

    return log


def stability(SOG, damping, manoeuvre):

    stability=[]

    for i in range(0, (len(SOG)-1-damping)):
        std = stat.stdev(SOG[i:(i+damping)])
        mean = stat.mean(SOG[i:(i+damping)])
        stab=(SOG[i]-mean)/std
        stability.append(stab)

    try:

        plt.figure('Stability')

        plt.plot(range(0, (len(SOG)-1-damping)), stability, color='black')

        for xc in manoeuvre:
            plt.axvline(x=xc, color='red', linestyle='--')

        plt.title("Stability of the SOG")
        plt.ylabel("Normalized SOG Error")
        plt.xlabel("Time")

        plt.savefig(r'Outputs\Images\Stability.png', bbox_inches='tight')

    except AttributeError:

        print('Stability not created')

    plt.close('all')


def legclean(slegs, dt, time_lim):  # It joins the short legs with the previous long one

    takelegs = []
    nicelegs = []
    index_lim = int(time_lim / dt)

    class Leg(object):
        def __init__(self, legstart, legstop, legmode, race, num, legs, man):
            self.Start = legstart
            self.Stop = legstop
            self.Mode = legmode
            self.Race = race
            self.Number = num
            self.Phases = legs
            self.Manoeuvres = man


    for leg in range(0, len(slegs)):
        if (slegs[leg].Phases > 3) and ((slegs[leg].Stop - slegs[leg].Start) > index_lim):
            takelegs.append(slegs[leg])

    nicelegs.append(takelegs[0])

    for leg in range(1, len(takelegs)):
        if (takelegs[leg].Mode==nicelegs[-1].Mode):
            newleg = Leg(nicelegs[-1].Start, takelegs[leg].Stop, nicelegs[-1].Mode, nicelegs[-1].Race,
                nicelegs[-1].Number, (takelegs[leg].Phases + nicelegs[-1].Phases), 0)
            nicelegs.remove(nicelegs[-1])
            nicelegs.append(newleg)

        else:
            nicelegs.append(takelegs[leg])

    # if time_lim:
    #     index_lim = int(time_lim / dt)
    #     longlegs = []
    #     slegs = nicelegs
    #
    #     for leg in range(0, len(slegs)):
    #         if ((slegs[leg].Stop - slegs[leg].Start) > index_lim):
    #             longlegs.append(slegs[leg])
    #
    #     for leg in range(1, len(longlegs)):
    #         if (longlegs[leg].Mode==nicelegs[-1].Mode):
    #             newleg = Leg(nicelegs[-1].Start, longlegs[leg].Stop, nicelegs[-1].Mode, nicelegs[-1].Race,
    #                 nicelegs[-1].Number, (longlegs[leg].Phases + nicelegs[-1].Phases), 0)
    #             nicelegs.remove(nicelegs[-1])
    #             nicelegs.append(newleg)
    #
    #         else:
    #             nicelegs.append(longlegs[leg])


    return nicelegs


def legcleanjoin(slegs, time_lim, dt): #It joins the short legs with the previous long one

    index_lim=int(time_lim/dt)
    longlegs=[]

    class Leg(object):
        def __init__(self, legstart, legstop, legmode, race, num, legs, man):
            self.Start = legstart
            self.Stop = legstop
            self.Mode = legmode
            self.Race = race
            self.Number = num
            self.Phases = legs
            self.Manoeuvres = man

    longlegs.append(slegs[0])

    for leg in range(1, len(slegs)):
        if ((slegs[leg].Stop-slegs[leg].Start)<index_lim):
            newleg = Leg(longlegs[-1].Start, slegs[leg].Stop, longlegs[-1].Mode, longlegs[-1].Race,
                longlegs[-1].Number, (slegs[leg].Phases + longlegs[-1].Phases), 0)
            longlegs.remove(longlegs[-1])
            longlegs.append(newleg)

        elif (slegs[leg].Mode==longlegs[-1].Mode):
            newleg = Leg(longlegs[-1].Start, slegs[leg].Stop, longlegs[-1].Mode, longlegs[-1].Race,
                longlegs[-1].Number, (slegs[leg].Phases + longlegs[-1].Phases), 0)
            longlegs.remove(longlegs[-1])
            longlegs.append(newleg)

        else:
            longlegs.append(slegs[leg])

    return longlegs


def analyzedlegs(log, legs, analysisstart, analysisend, dt, mans, params):
    race_mode=params['race_mode']
    courtesy_time=params['Race_Turn']
    time_lim=params['Minimum_Leg_Time']

    class Leg(object):
        def __init__(self, legstart, legstop, legmode, race, num, legs, man):
            self.Start = legstart
            self.Stop = legstop
            self.Mode = legmode
            self.Race = race
            self.Number = num
            self.Phases = legs
            self.Manoeuvres = man

    # TWAmean=np.mean(log.TWA)
    goodlegs=[]
    index_lim = int(time_lim / dt)

    for analysis in range(0,len(analysisstart)):

        if race_mode==True:

            #courtesy_time: to account for the case where the boat starts the new leg AFTER the start time
            usedlegs = [legp for legp in legs if legp.Stop >= (analysisstart[analysis]+int(courtesy_time/dt)) ]

            # A new starting leg will always be created, as to adjust to the analysis start times
            goodlegs.append(Leg(analysisstart[analysis], usedlegs[0].Stop, usedlegs[0].Mode, analysis+1,1,usedlegs[0].Phases,0))

            lat1=log.Latitude[int(goodlegs[0].Start)]
            lat2=log.Latitude[int(goodlegs[0].Stop)]
            lon1=log.Longitude[int(goodlegs[0].Start)]
            lon2=log.Longitude[int(goodlegs[0].Stop)]
            meandistmg=abs(latlon_to_metres(lat1, lat2, lon1, lon2))#*math.cos(abs(TWAmean-latlon_course(lat1, lat2, lon1, lon2))* math.pi / 180)) #Distance to which we'll compare
            meanspeed=np.mean(log.SOG_Kts[int(goodlegs[0].Start):int(goodlegs[0].Stop)])

            f=0
            for legpoint in range(1, len(usedlegs)):
                lat1=log.Latitude[int(usedlegs[legpoint].Start)]
                lat2=log.Latitude[int(usedlegs[legpoint].Stop)]
                lon1=log.Longitude[int(usedlegs[legpoint].Start)]
                lon2=log.Longitude[int(usedlegs[legpoint].Stop)]
                legdistmg=abs(latlon_to_metres(lat1, lat2, lon1, lon2))#*math.cos(abs(TWAmean-latlon_course(lat1, lat2, lon1, lon2))* math.pi / 180))

                if usedlegs[legpoint].Mode!='Reach' and (legdistmg<0.8*meandistmg): #If the leg is too short, it means
                    # it was actually not part of the race
                    break

                elif usedlegs[legpoint].Mode!='Reach' and (legdistmg>1.2*meandistmg):

                    step=0
                    endspeed=0

                    while (legdistmg>meandistmg or endspeed<0.6*meanspeed): # The leg distance may be right, but if the
                        # speed in the previous 30s is still too low it means there must be another point

                        step = step + 1
                        new_stop_point=int(usedlegs[legpoint].Stop-int(10/dt)*step)
                        lat2 = log.Latitude[(new_stop_point)]
                        lon2 = log.Longitude[(new_stop_point)]
                        legdistmg = abs(latlon_to_metres(lat1, lat2, lon1, lon2))# * math.cos(abs(TWAmean -latlon_course(lat1, lat2, lon1, lon2)) * math.pi / 180))
                        endspeed = np.mean(log.SOG_Kts[(new_stop_point-int(20/dt)):(new_stop_point)])


                    goodlegs.append(Leg(usedlegs[legpoint].Start, new_stop_point,
                                        usedlegs[legpoint].Mode, analysis + 1, legpoint + 1, usedlegs[legpoint].Phases,0))

                    break

                elif usedlegs[legpoint].Mode=='Reach' and usedlegs[legpoint-1].Mode=='Down': #Can't have reaching after downwind
                    break

                goodlegs.append(Leg(usedlegs[legpoint].Start, usedlegs[legpoint].Stop, usedlegs[legpoint].Mode,
                                    analysis+1, legpoint+1, usedlegs[legpoint].Phases,0))

                if usedlegs[legpoint].Mode=='Reach':
                    f=f+1
                else:
                    meandistmg=((legpoint-1-f)*meandistmg+legdistmg)/(legpoint-f) #Keeps perfecting the mean leg
                    # distance, ignoring the reaching legs

        elif race_mode == False:

            usedlegs = [legp for legp in legs if (legp.Stop >= analysisstart[analysis] and legp.Start <= analysisend[analysis])]

            if (usedlegs[0].Stop-analysisstart[analysis])>index_lim:
                goodlegs.append(Leg(analysisstart[analysis], usedlegs[0].Stop, usedlegs[0].Mode, analysis+1, 1, usedlegs[0].Phases,0))

            for legpoint in range(1, (len(usedlegs)-1)):
                goodlegs.append(Leg(usedlegs[legpoint].Start, usedlegs[legpoint].Stop, usedlegs[legpoint].Mode, analysis+1,
                                    1+legpoint, usedlegs[legpoint].Phases,0))

            if (analysisend[analysis] - usedlegs[-1].Start) > index_lim:
                goodlegs.append(Leg(usedlegs[-1].Start, analysisend[analysis], usedlegs[-1].Mode, analysis+1, len(usedlegs), usedlegs[-1].Phases,0))

    mans=[m for m in mans if m != '']

    for leg in range(0,len(goodlegs)):
        mani=[m for m in mans if (m >= goodlegs[leg].Start+1 and m <= goodlegs[leg].Stop-1)] # You can add margins so that small
        # stretches at the beginning and end are ignored (here the margins aer so that the turning maneuvre is ignored)
        goodlegs[leg].Manoeuvres=[goodlegs[leg].Start]+mani+[goodlegs[leg].Stop]



    if not params['no_man_legs']:
        goodlegs=[track for track in goodlegs if len(track.Manoeuvres)>2] # You can't have a leg with no maneouvres

    sign=-(log.Latitude[goodlegs[0].Stop] - log.Latitude[goodlegs[0].Start])

    return goodlegs, sign


def phaseclean(phases, treshold):

    SOG_upwind_preclean = []
    SOG_upwind_cut = []
    SOG_downwind_preclean = []

    upwind_phases_preclean = [ph for ph in phases if ph.mode == 'Up']

    downwind_phases_preclean = [ph for ph in phases if ph.mode == 'Down']


    for ph in upwind_phases_preclean:
        SOG_upwind_preclean.append(ph.speed_median)

    # maxSOGup=max(SOG_upwind_preclean)
    # minSOGup=min(SOG_upwind_preclean)
    meanup=np.mean(SOG_upwind_preclean)

    upwind_phases_cut = [ph for ph in upwind_phases_preclean if ph.speed_median >= meanup]

    # We now seek the mean of the upper values

    for ph in upwind_phases_cut:
        SOG_upwind_cut.append(ph.speed_median)

    meanupcut = np.mean(SOG_upwind_cut)


    upwind_phases = [ph for ph in upwind_phases_preclean if (ph.speed_median >= (1-treshold)*meanupcut and ph.speed_median <= (1+treshold)*meanupcut)]


    for ph in downwind_phases_preclean:
        SOG_downwind_preclean.append(ph.speed_median)

    # maxSOGdown=max(SOG_downwind_preclean)
    # minSOGdown=min(SOG_downwind_preclean)
    # meandown=0.5*(np.max(SOG_downwind_preclean)-np.min(SOG_downwind_preclean))
    meandown=np.mean(SOG_downwind_preclean)

    downwind_phases = [ph for ph in downwind_phases_preclean if ph.speed_median >= meandown]

    return upwind_phases, downwind_phases


def TackMode(log,ang_up,ang_down):

    modes=[]
    tacks=[]
    for i in range(0,len(log)):
        if log.TWA[i] <= ang_up:
            modes.append('U')
        elif log.TWA[i] >= ang_down:
            modes.append('D')
        elif ang_up < log.TWA[i] < ang_down:
            modes.append('O')

        if log.TWA[i] <= 0:
            tacks.append('P')
        elif log.TWA[i] > 0:
            tacks.append('S')

    return tacks, modes


def LegLog(log, AnalyzedLegs, race):

    colorpalette=['#AAAAAA', '#0074D9', '#FF851B', '#001f3f', '#01FF70', '#85144b', '#7FDBFF',
            '#FFDC00', '#FF4136', '#B10DC9', '#3D9970', '#AAAAAA', '#0074D9', '#FF851B', '#001f3f']

    leglog=['none']*len(log)
    colorlog=[colorpalette[0]]*len(log)

    color = 1
    if race==True:
        sum = 0
    else:
        sum = 10

    for leg in range(0,len(AnalyzedLegs)):
        leglog[AnalyzedLegs[leg].Start:AnalyzedLegs[leg].Stop]=['R' + str(AnalyzedLegs[leg].Race+sum) + 'L' +
                                        str(AnalyzedLegs[leg].Number)]*(AnalyzedLegs[leg].Stop-AnalyzedLegs[leg].Start)
        colorlog[AnalyzedLegs[leg].Start:AnalyzedLegs[leg].Stop] = [colorpalette[color]]*(AnalyzedLegs[leg].Stop-
                                                                                                AnalyzedLegs[leg].Start)
        color=color+1

    return leglog, colorlog


def PhaseLog(phases, AnalyzedLegs, race):

    AnalyzedPhases=[]
    pleglog= []
    pcolorlog= []

    colorpalette=['#AAAAAA', '#0074D9', '#FF851B', '#001f3f', '#01FF70', '#85144b', '#7FDBFF',
            '#FFDC00', '#FF4136', '#B10DC9', '#3D9970', '#AAAAAA', '#0074D9', '#FF851B', '#001f3f',
                  '#FFDC00', '#FF4136', '#B10DC9', '#3D9970', '#AAAAAA', '#0074D9', '#FF851B', '#001f3f',
                  '#FFDC00', '#FF4136', '#B10DC9', '#3D9970', '#AAAAAA', '#0074D9', '#FF851B', '#001f3f']

    color = 1

    if race==True:
        sum = 0
    else:
        sum = 10

    for leg in range(0, len(AnalyzedLegs)):
        phases_in_leg=[p for p in phases if (p.indexes[0] >= AnalyzedLegs[leg].Start and p.indexes[-1] <= AnalyzedLegs[leg].Stop
                                             and p.mode==AnalyzedLegs[leg].Mode)]
        AnalyzedPhases=AnalyzedPhases + phases_in_leg
        pleglog = pleglog + ['R' + str(AnalyzedLegs[leg].Race+sum) + 'L' + str(AnalyzedLegs[leg].Number)]*len(phases_in_leg)
        pcolorlog = pcolorlog + [colorpalette[color]]*len(phases_in_leg)
        color = color + 1

    return AnalyzedPhases, pleglog, pcolorlog


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx], idx


def color_scale(list):

    scale=['#00FFFF','#33FFFF','#66FFFF','#99FFFF','#CCFFFF','#FFCCCC','#FF9999','#FF6666','#FF3333','#FF0000']

    colors=[]
    list=list-min(list)
    if max(list)==0:
        list = list * (len(scale) - 1)
    else:
        list = list * (len(scale) - 1) / max(list)


    for i in range(0,len(list)):
        colors.append(scale[int(list[i])])

    return colors


def dtotarget(targets, twss, array):
    ds=[]
    for i in range(0, len(array)):
        [val,index]=find_nearest(targets[0], twss[i])
        ds.append(array[i]-targets[1][index])

    return ds


def dtotarget_point(targets, tws, val):

    [s,index]=find_nearest(targets[0], tws)
    ds=val-targets[1][index]
    perc=100*val/targets[1][index]

    return ds, perc


def delta_builder(modes, var, twss, targetup, targetdown):

    dis=[]
    pers=[]
    frac=[]

    for i in range(0, len(var)):

        if modes[i]=='U':
            dis.append(round(dtotarget_point(targetup, twss[i], var[i])[0],2))
            d=round(dtotarget_point(targetup, twss[i], var[i])[1], 2)
            pers.append(d)
            frac.append(round(d-100,2))

        elif modes[i]=='D':
            dis.append(round(dtotarget_point(targetdown, twss[i], var[i])[0],2))
            d=round(dtotarget_point(targetdown, twss[i], var[i])[1], 2)
            pers.append(d)
            frac.append(round(d-100,2))

        else:
            dis.append(0)#OJO
            pers.append(0)
            frac.append(0)

    return dis, pers, frac


def EventFile(log, legs, phases, params, pleglog, event, tbef, taf):
    temp = open('source\\Event_Template.dat','r')

    name = params['Name']
    mode = params['race_mode']
    list=[]

    for line in temp:
        list.append(line)
        if line == '<daysail>\n':
            list.append('  <boat val="' + name + '" />\n'
                        '  <confignum val="0" />\n'
                        '  <date val="' + str(log.Date_Time[1])[0:10] + '" />\n')

        if line == '  <daytype val="33" />\n':
            if mode==True:
                list.append('  <daytypestr val="Racing" />\n')
            else:
                list.append('  <daytypestr val="Training; Other" />\n')

        if line == '  <dailycomments>\n':
            list.append('    <boatname val="' + name + '" />\n'
                        '    <date val="' + str(log.Date_Time[1])[0:10] + '" />\n')
        if line=='  <events>\n':
            list = Events_event(list,log,legs)
        if line=='  <phases>\n':
            list = Events_phases(list, phases, pleglog)
        if line=='  <tackjibes>\n':
            list = Events_mans(list, event, tbef, taf)
#        if line=='  <tackjibes>\n':
#            tackline=cursor+1
#        if line=='  <sailchanges>\n':
#            sailline=cursor+1

    temp.close()
    file = open('Outputs\\Events_'+name+'_'+ str(log.Date_Time[1])[0:10] + '.xml','w')
    file.writelines(list)
    file.close()

    return []


def Events_mans(list, event, tbefore, tafter):

    g=0
    t=0
    tackend=0
    gybeend=0
    tbefore=str(tbefore)
    tafter=str(tafter)

    for i in range(len(event['man_times'])):
        if ((event['gybes_indexes'][g] < event['tacks_indexes'][t] or tackend == 1) and gybeend == 0):
            time = str(event['gybing_times'][g])
            g += 1
            if type(event['gybes_indexes'][g]) == str:
                gybeend = 1
                g -= 1
            tack = 'false'

        elif ((event['gybes_indexes'][g] > event['tacks_indexes'][t] or gybeend == 1) and tackend == 0):
            time = str(event['tacking_times'][t])
            t += 1
            if type(event['tacks_indexes'][t]) == str:
                tackend = 1
                t -= 1
            tack = 'true'

        list.append('    <tackjibe datetime="'+time+'" istack="'+tack+'" isvalidcalib="true" isvalidperf="true"'
                    ' timebefore="'+tbefore+'" timeafter="'+tafter+'" avgtime="20" fixwind="False" isdeleted="false" errcode="1" '
                    'errmsg="" />\n')

        if (gybeend==1 and tackend==1):
            break

    return list


def Events_phases(list, phases, pleglog):

    for i in range(len(phases)):
        if phases[i].mode=='Up':
            mstr= '1'
        elif phases[i].mode=='Down':
            mstr = '8'
        else:
            mstr = '4'

        if len(pleglog[i])==5:
            race=pleglog[i][1:3]
            raceleg = pleglog[i][4]
        else:
            race=pleglog[i][1]
            raceleg = pleglog[i][3]

        list.append('    <phase name="Fram_NormedPhase_'+ str(phases[i].start_time.year)+str(phases[i].start_time)[5:7]+
                    str(phases[i].start_time)[8:10]+'_'+str(phases[i].start_time)[11:13]+str(phases[i].start_time)[14:16]+
                    str(phases[i].start_time)[17:19] +'">\n'
                    '      <startdatetime val="'+str(phases[i].start_time)+'" />\n'
                    '      <sailsup val="Sails" />\n'
                    '      <duration val="'+str(int(phases[i].duration))+'" />\n'
                    '      <phasetype val="128" />\n'
                    '      <phasenum val="0" />\n'
                    '      <phasetypestr val="Other" />\n'
                    '      <racenum val="'+race+'" />\n'
                    '      <racelegnum val="'+raceleg+'" />\n'
                    '      <sailingmode val="'+mstr+'" />\n'
                    '      <opponentname val="" />\n'
                    '      <balancetype val="0" />\n'
                    '      <phasemadeonboard val="False" />\n'
                    '      <comments val="" />\n'
                    '      <testsubject val="" />\n'
                    '      <testrating val="0" />\n'
                    '    </phase>\n')

    return list


def evbuild(date, type, att):
    string = '    <event date="'+str(date)[0:10]+'" time="'+str(date)[11:19]+'" type="'+type+'" attribute="'+att+'" comments="" labelalign="Top" />\n'
    return string


def Events_event(list,log,legs):
    list.append(evbuild(log.Date_Time[1], 'DayStart', '0'))
    list.append(evbuild(log.Date_Time[5], 'SailsUp', 'Sails;;'))
    list.append(evbuild(log.Date_Time[legs[0].Start], 'RaceStartGun', '1'))

    for i in range(len(legs)-1):
        list.append(evbuild(log.Date_Time[legs[i].Stop], 'RaceMark', '1'))

    list.append(evbuild(log.Date_Time[legs[-1].Stop], 'RaceFinish', '1'))
    list.append(evbuild(log.Date_Time[1], 'DayStop', '0'))

    return list


def load_targets(trgt_dir, tws_min_up, tws_max_up, tws_min_down, tws_max_down):
    all_files = os.listdir(trgt_dir)

    targets = {}

    for file in all_files:

        if 'Dn' in file:
            dir = trgt_dir + '\\' + file
            cur_file = open(dir)
            TWS_trgt_values = []
            trgt_values = []

            for line in cur_file:
                key_value = line.split()
                if len(key_value) == 2 and key_value[1] != 'BSP' and key_value[1] != 'TWA' and tws_min_down <= float(key_value[0]) <= tws_max_down:
                    TWS_trgt_values.append(float(key_value[0].strip()))
                    trgt_values.append(float(key_value[1].strip()))

                if '///' in key_value:
                    break



            [TWS_trgt_values, trgt_values] = create_trend(TWS_trgt_values, trgt_values)
            target_couple = [TWS_trgt_values, trgt_values]
            name = file.strip('.txt')
            targets[name] = target_couple

            cur_file.close()

        elif 'Up' in file:
            dir = trgt_dir + '\\' + file
            cur_file = open(dir)
            TWS_trgt_values = []
            trgt_values = []

            for line in cur_file:
                key_value = line.split()
                if len(key_value) == 2 and key_value[1] != 'BSP' and key_value[1] != 'TWA' and tws_min_up <= float(key_value[0]) <= tws_max_up:
                    TWS_trgt_values.append(float(key_value[0].strip()))
                    trgt_values.append(float(key_value[1].strip()))

                if '///' in key_value:
                    break

            [TWS_trgt_values, trgt_values] = create_trend(TWS_trgt_values, trgt_values)
            target_couple = [TWS_trgt_values, trgt_values]
            name = file.strip('.txt')
            targets[name] = target_couple

            cur_file.close()

    targets['VMGvsTWS_DOWN'] = [TWS_trgt_values, targets['DnBsp'][1] * abs(np.cos(targets['DnTwa'][1]*math.pi/180))]
    targets['VMGvsTWS_UP'] = [TWS_trgt_values, targets['UpBsp'][1] * abs(np.cos(targets['UpTwa'][1] *math.pi/180))]

    return targets


def LiftShiftOriginal(leg,log,mode,reference, man_inds):
    man_inds=int(man_inds)

    lift = []
    signs = []

    if reference=='Axis':
        bearing = latlon_course360(log.Latitude[leg.Start], log.Latitude[leg.Stop], log.Longitude[leg.Start],
                               log.Longitude[leg.Stop])
    elif reference=='Wind':
        bearing = angles_stats(log.TWD[leg.Start:leg.Stop],'Mean')
        if leg.Mode=='Down':
            bearing+=180
            if bearing>360:
                bearing-=360

    cogs=rotate_angles_180(log.COG[leg.Start:leg.Stop], -bearing)

    legb = 0
    for stretch in range(0, (len(leg.Manoeuvres) - 1)):

        strb = rotate_angles_180([latlon_course(log.Latitude[leg.Manoeuvres[stretch]], log.Latitude[leg.Manoeuvres[stretch + 1]],
                                log.Longitude[leg.Manoeuvres[stretch]],
                                log.Longitude[leg.Manoeuvres[stretch + 1]])],-bearing)[0]

        if strb<0:
            signs.append(-1)
        else:
            signs.append(1)

        legb += abs(strb)*(leg.Manoeuvres[stretch + 1]-leg.Manoeuvres[stretch])

    legb = legb / (leg.Stop-leg.Start)

    relmans=pd.Series(leg.Manoeuvres)-leg.Start

    if mode == 'Lift':
        lift=[-(abs(cog) - legb) for cog in cogs] # if negative, you are lifting

    elif mode == 'Dir':
        for i in range(0, (len(relmans) - 1)):
            lift+=[(cog - signs[i]*legb) for cog in cogs[(relmans[i]):(relmans[i+1])]]

    lift=lowpass(lift, 0.1)

    colors = ['None'] * len(lift)
    colors[:man_inds] = ['lightgray'] * man_inds
    lift[:man_inds] = [0] * man_inds
    colors[-man_inds:] = ['lightgray'] * man_inds
    lift[-man_inds:] = [0] * man_inds
    for man in relmans[1:-1]:
        if man_inds>man:
            man=man_inds
        elif man + man_inds>len(lift):
            man=len(lift)-man_inds
        lift[(man - man_inds):(man + man_inds)] = [0] * man_inds * 2
        colors[(man - man_inds):(man + man_inds)] = ['lightgray'] * man_inds * 2

    if leg.Mode=='Down':
        legb=180-legb

    return lift, legb, legb, colors


def LiftShift(leg,log,mode,reference, man_inds):
    man_inds=int(man_inds)

    lift = []
    signs = []

    if reference=='Axis':
        bearing = latlon_course360(log.Latitude[leg.Start], log.Latitude[leg.Stop], log.Longitude[leg.Start],
                               log.Longitude[leg.Stop])
    elif reference=='Wind':
        bearing = angles_stats(log.TWD[leg.Start:leg.Stop],'Mean')
        if leg.Mode=='Down':
            bearing+=180
            if bearing>360:
                bearing-=360

    cogs=rotate_angles_180(log.COG[leg.Start:leg.Stop], -bearing)

    middle_man=math.floor(0.5*(len(leg.Manoeuvres)))

    legb = 0
    for stretch in range(0, middle_man):

        strb = rotate_angles_180([latlon_course(log.Latitude[leg.Manoeuvres[stretch]], log.Latitude[leg.Manoeuvres[stretch + 1]],
                                log.Longitude[leg.Manoeuvres[stretch]],
                                log.Longitude[leg.Manoeuvres[stretch + 1]])],-bearing)[0]

        if strb<0:
            signs.append(-1)
        else:
            signs.append(1)

        legb += abs(strb)*(leg.Manoeuvres[stretch + 1]-leg.Manoeuvres[stretch])

    legb1 = legb / (leg.Manoeuvres[middle_man]-leg.Start)

    legb = 0
    for stretch in range(middle_man, (len(leg.Manoeuvres)-1)):

        strb = rotate_angles_180([latlon_course(log.Latitude[leg.Manoeuvres[stretch]], log.Latitude[leg.Manoeuvres[stretch + 1]],
                                log.Longitude[leg.Manoeuvres[stretch]],
                                log.Longitude[leg.Manoeuvres[stretch + 1]])],-bearing)[0]

        if strb<0:
            signs.append(-1)
        else:
            signs.append(1)

        legb += abs(strb)*(leg.Manoeuvres[stretch + 1]-leg.Manoeuvres[stretch])

    legb2 = legb / (leg.Stop-leg.Manoeuvres[middle_man])

    legbs=np.linspace(legb1, legb2, len(cogs))

    relmans=pd.Series(leg.Manoeuvres)-leg.Start

    if mode == 'Lift':
        lift=[-(abs(cogs[i]) - legbs[i]) for i in range(len(cogs))] # if negative, you are lifting

    elif mode == 'Dir':
        for s in range(0, (len(relmans) - 1)):
            lift+=[(cogs[i] - signs[s]*legbs[i]) for i in range(relmans[i],relmans[i+1])]

    lift=lowpass(lift, 0.1)

    colors = ['None'] * len(lift)
    colors[:man_inds] = ['lightgray'] * man_inds
    lift[:man_inds] = [0] * man_inds
    colors[-man_inds:] = ['lightgray'] * man_inds
    lift[-man_inds:] = [0] * man_inds
    for man in relmans[1:-1]:
        if man_inds>man:
            man=man_inds
        elif man + man_inds>len(lift):
            man=len(lift)-man_inds
        lift[(man - man_inds):(man + man_inds)] = [0] * man_inds * 2
        colors[(man - man_inds):(man + man_inds)] = ['lightgray'] * man_inds * 2

    if leg.Mode=='Down':
        legb1=180-legb1
        legb2 = 180 - legb2

    return lift, legb1, legb2, colors


def Event_Time_Read(log, filename, dt):
    temp = open(filename, 'r')

    starts = []
    stops = []

    for line in temp:

        if 'RaceStartGun' in line:
            t = line.index('time=')
            d = line.index('date=')
            starts.append(datetoindex(pd.to_datetime(line[(d+6):(d+16)]+' '+line[(t+6):(t+14)]), log, dt))

        if 'RaceFinish' in line:
            t = line.index('time=')
            d = line.index('date=')
            stops.append(datetoindex(pd.to_datetime(line[(d+6):(d+16)]+' '+line[(t+6):(t+14)]), log, dt))

    temp.close()

    return [starts, stops]


def Marks(log, legs):
    lats=[]
    lons=[]
    for i in range(0,len(legs)-1):
        if (legs[i].Mode=='Up' and legs[i+1].Mode=='Down'):
            lats.append(np.mean([log.Latitude[legs[i].Stop], log.Latitude[legs[i+1].Start]]))
            lons.append(np.mean([log.Longitude[legs[i].Stop], log.Longitude[legs[i + 1].Start]]))
        elif (legs[i].Mode=='Down' and legs[i+1].Mode=='Up'):
            lats.append(np.mean([log.Latitude[legs[i].Stop], log.Latitude[legs[i+1].Start]]))
            lons.append(np.mean([log.Longitude[legs[i].Stop], log.Longitude[legs[i + 1].Start]]))
        elif legs[i].Mode=='Reach':
            lats.append(log.Latitude[legs[i].Start])
            lats.append(log.Latitude[legs[i].Stop])
            lons.append(log.Longitude[legs[i].Start])
            lons.append(log.Longitude[legs[i].Stop])

    return lats, lons


def CleanUtc(list):

    goodtime = []
    for i in list:
        time = xlrd.xldate_as_datetime(float(i), 0)
        if time.microsecond > 500000:
            time = time + datetime.timedelta(seconds=1)
        goodtime.append(pd.Timestamp(time.strftime("%Y-%m-%d %H:%M:%S")))

    return goodtime


def color_scale_values(list, cscale, values):

    colors=[]

    values=[float(i) for i in values]
    list = [float(i) for i in list]

    for ins in list:
        if np.isnan(ins):
            colors.append(cscale[0])
        else:
            for i in range(len(values)+1):
                if i == 0:
                    if ins <= values[0]:
                        colors.append(cscale[0])
                        break

                elif i==len(values):
                    if ins > values[-1]:
                        colors.append(cscale[-1])
                        break

                else:
                    if (ins <= values[i] and ins > values[i-1]):
                        colors.append(cscale[i])
                        break

    return colors


def Wind_Dir(log, cogs, sogs, mean_sog, best_turns=[]): #For particular cases, we still want to take into account the SOGs of the whole data
    best_turn=np.argmax(sogs) #Divide the in two sides, with one of the sides having the best manoeuvre in the middle
    cogs_centered=[]
    for i in cogs:
        angle=i-cogs[best_turn]
        if angle<-180:
            angle+=360
        elif angle>180:
            angle-=360
        cogs_centered.append(angle)

    if not best_turns: #In the segments, its better to calculate this beforehand
        best_turns = [i for i in range(len(sogs)) if sogs[i] > 0.7*mean_sog] #Take only into account the best ones, antes 0.6
    cogs_centered = [cogs_centered[i] for i in best_turns]

    side1 = [i for i in cogs_centered if abs(i) < 90]+[0] #to reinforce tendencies
    side2 = [i for i in cogs_centered if abs(i) > 90]+[180]

    #Choose the better side with the mean speeds
    spd1 = []
    spd2 = []
    for i in range(len(log.COG)):
        angle=log.COG[i]-cogs[best_turn]
        if angle<-180:
            angle+=360
        elif angle>180:
            angle-=360
        if abs(angle) < 90:
            spd1.append(log.SOG_Kts[i])
        else:
            spd2.append(log.SOG_Kts[i])

    if max(spd1)<max(spd2): #take only the side with more speed (supposedly the downwind side)
        side1t = [i-180 for i in side1]
        medw = angles_stats(side2+side1t,'Mean')+cogs[best_turn]-180
    else:
        side2t = [i - 180 for i in side2]
        medw = angles_stats(side1+side2t, 'Mean')+cogs[best_turn]-180

    if medw>360:
        medw-=360
    elif medw<0:
        medw+=360

    return medw


########################################################################################################################


def calculate_sog(lat, lon, time, dt):
    SOG = []
    # dist=[]
    SOG.append(0)

    for i in range(1, len(time)):
        d=latlon_to_metres(lat[i - 1], lat[i], lon[i - 1], lon[i])
        SOG.append(d/dt)
        # dist.append(d*0.000539957)

    return SOG


def calculate_cog(lat, lon, time):
    COG = [0]

    for i in range(1, len(time)):
        if lon[i] == lon[i - 1] and lat[i] == lat[i - 1]:
            COG.append(COG[i - 1])
        else:
            COG.append(latlon_course(lat[i - 1], lat[i], lon[i - 1], lon[i]))

    return COG


def calculate_cog_NoFilter(lat, lon, time):
    COG = [0]

    for i in range(1, len(time)):
        if lon[i] == lon[i - 1] and lat[i] == lat[i - 1]:
            COG.append(COG[i - 1])
        else:
            COG.append(latlon_course360(lat[i - 1], lat[i], lon[i - 1], lon[i]))
            if COG[i] < 0:
                COG[i] = COG[i] + 360
            elif COG[i] > 360:
                COG[i] = COG[i] - 360

    return COG


def manoeuvres_1(dt, time, COG, speed, tacking_angle, maneuver_angle, time_1_hdg_before,
                 time_2_hdg_before, time_1_hdg_after, time_2_hdg_after, time_hdgmax, TWD_is_present):
    COG = COG.tolist()

    manoeuvres = []
    man_indexes = []
    tacks = []
    tacks_indexes = []
    TWD_tack = []

    """ INDEX DEFINITION FOR THE WANDS """

    index_hdgmax = int(time_hdgmax / dt)

    index_1_hdg_before = int(time_1_hdg_before / dt)
    index_2_hdg_before = int(time_2_hdg_before / dt)
    index_1_hdg_after = int(time_1_hdg_after / dt)
    index_2_hdg_after = int(time_2_hdg_after / dt)

    index_max = max(index_hdgmax, index_2_hdg_before, index_2_hdg_after)

    """ WAND INITIALIZATION """

    HDG_wand_before = [0] * index_max
    HDG_wand_after = [0] * index_max
    HDG_mean_before = [0] * index_max
    HDG_mean_after = [0] * index_max
    delta_HDG = [0] * index_max
    dheading_wands = [0] * index_max
    max_dheading = [0] * index_max

    for i in range(index_max, len(time) - index_max):
        """ HEADING WAND BEFORE THE POINT WITH INDEX i """
        HDG_wand_before.append(COG[i - index_2_hdg_before: i - index_1_hdg_before + 1])
        HDG_mean_before.append(stats.circmean(HDG_wand_before[i], high=360))

        """ HEADING WAND AFTER THE POINT WITH INDEX i """
        HDG_wand_after.append(COG[i + index_1_hdg_after: i + index_2_hdg_after + 1])
        HDG_mean_after.append(stats.circmean(HDG_wand_after[i], high=360))

        delta_HDG.append(
            min(abs(HDG_mean_after[i] - HDG_mean_before[i]), 360 - abs(HDG_mean_after[i] - HDG_mean_before[i])))

    for i in range(index_max, len(time) - index_max):
        """ DELTA-HEADING WAND (CENTERED ON i) + MAX_VALUE """
        dheading_wands.append(delta_HDG[i - index_hdgmax: i + index_hdgmax + 1])
        max_dheading.append(max(dheading_wands[i]))

    for i in range(index_max, len(time) - index_max):
        if delta_HDG[i] > maneuver_angle:
            if delta_HDG[i] == max_dheading[i] and np.mean(speed[i - index_hdgmax: i + index_hdgmax + 1]) > 2:

                manoeuvres.append(time[i])
                man_indexes.append(i)

                if 150 > delta_HDG[i] > tacking_angle and not TWD_is_present:
                    tacks.append(time[i])
                    tacks_indexes.append(i)

                    TWD_tack.append(stats.circmean([HDG_mean_before[i], HDG_mean_after[i]], high=360))

    if not TWD_is_present:
        return manoeuvres, tacks, man_indexes, tacks_indexes, TWD_tack
    elif TWD_is_present:
        return manoeuvres, man_indexes


def manoeuvres_gpx_easy_API(dt, time, TWA, speed, COG, tack_wand, gybe_wand, speed_treshold_perc):
    TWA = TWA.tolist()
    #quantile_speed = np.percentile(speed, 25)
    #speed = speed.tolist()
    # quantile_speed = np.percentile(speed, 25)
    # speed = speed.tolist()
    tacking_indexes = []
    gybing_indexes = []
    maneuvers_indexes = []
    tacking_deltaTWA = []
    gybing_deltaTWA = []

    index_tack_before_1 = int((tack_wand[0]+tack_wand[2]) / dt)
    index_gybe_before_1 = int((gybe_wand[0]+gybe_wand[2]) / dt)
    index_tack_before_2 = int(tack_wand[0] / dt)
    index_gybe_before_2 = int(gybe_wand[0] / dt)
    index_tack_after_1 = int((tack_wand[1]-tack_wand[2]) / dt)
    index_gybe_after_1 = int((gybe_wand[1]-gybe_wand[2]) / dt)
    index_tack_after_2 = int(tack_wand[1] / dt)
    index_gybe_after_2 = int(gybe_wand[1] / dt)
    index_max = max(index_tack_before_1, index_gybe_before_1)

    speed_treshold = np.mean(speed)*speed_treshold_perc

    for i in range(index_max, len(time) - index_max):

        if np.sign(TWA[i]) != np.sign(TWA[i + 1]):

            if abs(TWA[i-index_tack_before_1])<90:
                """ TWA WAND BEFORE THE POINT WITH INDEX i """
                TWA_mean_before = angles_stats(TWA[i - index_tack_before_1: i - index_tack_before_2 + 1], 'Mean', twa=True)
                """ TWA WAND AFTER THE POINT WITH INDEX i """
                TWA_mean_after = angles_stats(TWA[i + index_tack_after_1: i + index_tack_after_2 + 1], 'Mean', twa=True)
                """ HEADING WAND BEFORE THE POINT WITH INDEX i """
                HDG_mean_before = stats.circmean(COG[i - index_tack_before_1: i - index_tack_before_2 + 1], high=360)
                """ TWA WAND AFTER THE POINT WITH INDEX i """
                HDG_mean_after = stats.circmean(COG[i + index_tack_after_1: i + index_tack_after_2 + 1], high=360)
                delta_HDG = min(abs(HDG_mean_after - HDG_mean_before), 360 - abs(HDG_mean_after - HDG_mean_before))

                SOG_mean_before = np.mean(speed[i - index_tack_before_1: i - index_tack_before_2 + 1])
                SOG_mean_after = np.mean(speed[i + index_tack_after_1: i + index_tack_after_2 + 1])

                if np.sign(TWA_mean_before) != np.sign(TWA_mean_after) and delta_HDG > 20 and SOG_mean_before>speed_treshold \
                        and SOG_mean_after>speed_treshold:
                    maneuvers_indexes.append(i)
                    tacking_indexes.append(i)
                    tacking_deltaTWA.append(min(abs(TWA_mean_before-TWA_mean_after), 360-abs((TWA_mean_before-TWA_mean_after))))

            else:
                """ TWA WAND BEFORE THE POINT WITH INDEX i """
                TWA_mean_before = angles_stats(TWA[i - index_gybe_before_1: i - index_gybe_before_2 + 1], 'Mean', twa=True)
                """ TWA WAND AFTER THE POINT WITH INDEX i """
                TWA_mean_after = angles_stats(TWA[i + index_gybe_after_1: i + index_gybe_after_2 + 1], 'Mean', twa=True)
                """ HEADING WAND BEFORE THE POINT WITH INDEX i """
                HDG_mean_before = stats.circmean(COG[i - index_gybe_before_1: i - index_gybe_before_2 + 1], high=360)
                """ TWA WAND AFTER THE POINT WITH INDEX i """
                HDG_mean_after = stats.circmean(COG[i + index_gybe_after_1: i + index_gybe_after_2 + 1], high=360)
                delta_HDG = min(abs(HDG_mean_after - HDG_mean_before), 360 - abs(HDG_mean_after - HDG_mean_before))

                SOG_mean_before = np.mean(speed[i - index_gybe_before_1: i - index_gybe_before_2 + 1])
                SOG_mean_after = np.mean(speed[i + index_gybe_after_1: i + index_gybe_after_2 + 1])

                if np.sign(TWA_mean_before) != np.sign(TWA_mean_after) and delta_HDG > 20 and SOG_mean_before>speed_treshold \
                        and SOG_mean_after>speed_treshold:
                    maneuvers_indexes.append(i)
                    gybing_indexes.append(i)
                    gybing_deltaTWA.append(min(abs(TWA_mean_before-TWA_mean_after), 360-abs((TWA_mean_before-TWA_mean_after))))


    return maneuvers_indexes, tacking_deltaTWA, tacking_indexes, gybing_deltaTWA, gybing_indexes


def calculate_TWD(reading_time, time, TWD_list, man):
    TWD = []
    first = True
    last = False
    k = 0
    reading_time = reading_time.tolist()
    time = time.tolist()
    TWD_list = TWD_list.tolist()

    if not man:
        for j in range(0, len(time)):

            if time[j] != reading_time[k]:

                if first:
                    TWD.append(TWD_list[k])
                elif last:
                    TWD.append(TWD_list[k])
                elif not last and not first:
                    TWD.append(
                        TWD_list[k - 1] + (TWD_list[k] - TWD_list[k - 1]) * TimeDelta(reading_time[k - 1], time[j]) /
                        TimeDelta(reading_time[k - 1], reading_time[k]))

            if time[j] == reading_time[k]:

                TWD.append(TWD_list[k])
                if type(TWD_list[k + 1]) != str:
                    k += 1
                    first = False
                else:
                    last = True

    elif man:
        for j in range(0, len(time)):

            if time[j] != reading_time[k]:

                if first:
                    TWD.append(TWD_list[k])
                elif last:
                    TWD.append(TWD_list[k])
                elif not last and not first:
                    TWD.append(
                        TWD_list[k - 1] + (TWD_list[k] - TWD_list[k - 1]) * TimeDelta(reading_time[k - 1], time[j]) /
                        TimeDelta(reading_time[k - 1], reading_time[k]))

            elif time[j] == reading_time[k]:
                TWD.append(TWD_list[k])
                if k + 1 < len(TWD_list):
                    k += 1
                    first = False
                else:
                    last = True

    return TWD


def calculate_TWS(reading_time, time, TWD_list):
    TWS = []
    first = True
    last = False
    k = 0

    for j in range(0, len(time)):

        if time[j] != reading_time[k]:

            if first:
                TWS.append(TWD_list[k])
            elif last:
                TWS.append(TWD_list[k])
            elif not last and not first:
                TWS.append(TWD_list[k - 1] + (TWD_list[k] - TWD_list[k - 1]) * TimeDelta(reading_time[k - 1], time[j]) /
                           TimeDelta(reading_time[k - 1], reading_time[k]))

        elif time[j] == reading_time[k]:
            TWS.append(TWD_list[k])
            if k + 1 < len(TWD_list):
                k += 1
                first = False
            else:
                last = True

    return TWS


def calculate_VMC(leg, log, SOG):
    bearing = latlon_course360(log.Latitude[leg.Start], log.Latitude[leg.Stop], log.Longitude[leg.Start],
                               log.Longitude[leg.Stop])
    VMC = []
    courseang=[]

    for i in range(leg.Start, leg.Stop):

        a = bearing - log.COG[i]
        if a > 180:
            a -= 360
        if a < -180:
            a += 360

        courseang.append(a)

        a = SOG[i]*np.cos(a*np.pi/180)

        VMC.append(a)

    return pd.Series(VMC), pd.Series(courseang), bearing



def calculate_TWA(time, TWD, HDG):
    diff = []

    for i in range(0, len(time)):

        a = TWD[i] - HDG[i]
        if a > 180:
            a -= 360
        if a < -180:
            a += 360

        diff.append(a)

    # corr = angles_stats(diff, 'Mean', twa=True)
    #
    # for i in range(0, len(diff)):
    #     diff[i] -= corr

    return diff


def manoeuvres_2(man_indexes_1, TWA, time, dt, mag_hdg, time_1_hdg_before, time_2_hdg_before, time_1_hdg_after,
                 time_2_hdg_after, time_1_TWA, time_2_TWA, up_down_twa_limit, TWD_is_present):
    TWA = TWA.tolist()
    man_indexes_1 = man_indexes_1.tolist()
    mag_hdg = mag_hdg.tolist()

    man_indexes_1 = list(filter(None, man_indexes_1))

    tacking_times_2 = []
    tacking_indexes_2 = []
    gybing_times_2 = []
    gybing_indexes_2 = []
    maneuvers_times_2 = []
    maneuvers_indexes_2 = []
    TWD_at_man = []

    index_1_hdg_before = int(time_1_hdg_before / dt)
    index_2_hdg_before = int(time_2_hdg_before / dt)
    index_1_hdg_after = int(time_1_hdg_after / dt)
    index_2_hdg_after = int(time_2_hdg_after / dt)

    index_TWA_1_before = int(time_1_TWA / dt)
    index_TWA_2_before = int(time_2_TWA / dt)
    index_TWA_1_after = int(time_1_TWA / dt)
    index_TWA_2_after = int(time_2_TWA / dt)
    index_max = max(index_TWA_1_before, index_TWA_2_before, index_TWA_1_after, index_TWA_2_after)

    HDG_wand_before = [0] * index_max
    HDG_wand_after = [0] * index_max
    HDG_mean_before = [0] * index_max
    HDG_mean_after = [0] * index_max
    delta_HDG = [0] * index_max
    TWA_wand_before = [0] * index_max
    TWA_wand_after = [0] * index_max
    TWA_mean_before = [0] * index_max
    TWA_mean_after = [0] * index_max

    for i in range(index_max, len(time) - index_max):
        """ HEADING WAND BEFORE THE POINT WITH INDEX i """
        HDG_wand_before.append(mag_hdg[i - index_2_hdg_before: i - index_1_hdg_before + 1])
        HDG_mean_before.append(stats.circmean(HDG_wand_before[i], high=360))

        """ HEADING WAND AFTER THE POINT WITH INDEX i """
        HDG_wand_after.append(mag_hdg[i + index_1_hdg_after: i + index_2_hdg_after + 1])
        HDG_mean_after.append(stats.circmean(HDG_wand_after[i], high=360))

        delta_HDG.append(
            min(abs(HDG_mean_after[i] - HDG_mean_before[i]), 360 - abs(HDG_mean_after[i] - HDG_mean_before[i])))

        """ TWA WAND BEFORE THE POINT WITH INDEX i """
        TWA_wand_before.append(TWA[i - index_TWA_2_before: i - index_TWA_1_before + 1])
        TWA_mean_before.append(stat.median(TWA_wand_before[i]))

        """ TWA WAND AFTER THE POINT WITH INDEX i """
        TWA_wand_after.append(TWA[i + index_TWA_1_after: i + index_TWA_2_after + 1])
        TWA_mean_after.append(stat.median(TWA_wand_after[i]))

    for i in man_indexes_1:

        if abs(TWA[i - index_TWA_1_before]) < up_down_twa_limit and np.sign(TWA_mean_after[i]) != np.sign(
                TWA_mean_before[i]):
            tacking_times_2.append(time[i])
            tacking_indexes_2.append(i)
            maneuvers_times_2.append(time[i])
            maneuvers_indexes_2.append(i)
            TWD_at_man.append(stats.circmean([HDG_mean_before[i], HDG_mean_after[i]], high=360))

        elif abs(TWA[i - index_TWA_1_before]) >= up_down_twa_limit and np.sign(TWA_mean_after[i]) != np.sign(
                TWA_mean_before[i]):
            gybing_times_2.append(time[i])
            gybing_indexes_2.append(i)
            maneuvers_times_2.append(time[i])
            maneuvers_indexes_2.append(i)
            TWD_gybe = 180 + stats.circmean([HDG_mean_before[i], HDG_mean_after[i]], high=360)
            if TWD_gybe > 360:
                TWD_gybe -= 360
            TWD_at_man.append(TWD_gybe)

    twd_mean = stats.circmean(TWD_at_man, high=360)

    for i in range(1, len(TWD_at_man)):
        if abs(TWD_at_man[i] - twd_mean) > 45:
            TWD_at_man[i] = TWD_at_man[i - 1]
    if not TWD_is_present:
        return tacking_times_2, tacking_indexes_2, gybing_times_2, gybing_indexes_2, maneuvers_times_2, maneuvers_indexes_2, TWD_at_man
    elif TWD_is_present:
        return tacking_times_2, tacking_indexes_2, gybing_times_2, gybing_indexes_2, maneuvers_times_2, maneuvers_indexes_2


def calculate_VMG(SOG, time, TWA, lowpass_cutout_freq):
    VMG = []

    for i in range(0, len(time)):
        VMG.append(abs(SOG[i] * math.cos(TWA[i] * math.pi / 180)))
        # if abs(SOG[i] * math.cos(abs(TWA[i] * math.pi / 180)))=='Nan':
        #     VMG=1

    #I dont know why it doesnt work
    # VMG = lowpass(VMG, lowpass_cutout_freq)

    return VMG


def create_phases_App(speed, time, dt, TWA, heel, pitch, VMG, gyro_Y, gyro_X, Acc_X, man_indexes,
                      man_wand_to_avoid_before, man_wand_to_avoid_after,
                      phase_length, std_twa_limit, speed_median_min):
    speed = speed.tolist()
    TWA = TWA.tolist()
    gyro_Y = gyro_Y.tolist()
    VMG = VMG.tolist()
    gyro_X = gyro_X.tolist()
    Acc_X = Acc_X.tolist()
    pitch = pitch.tolist()
    heel = heel.tolist()
    man_indexes = man_indexes.tolist()
    man_indexes = list(filter(None, man_indexes))

    print('average speed: ', np.mean(speed))
    print('average heel: ', np.mean(heel))
    print('average pitch: ', np.mean(pitch))

    class Phase(object):

        def __init__(self, indexes, speed_median, TWA_mean_abs, TWA_mean, Acc_mean, Heel_mean, Pitch_mean,
                     speed_consistancy, gyro_Y, gyro_X, max_acc_x, mean_VMG, mean_time, time_index):
            self.indexes = indexes
            self.speed_median = speed_median
            self.TWA_mean_abs = TWA_mean_abs
            self.TWA_mean = TWA_mean
            self.Heel_mean = Heel_mean
            self.Pitch_mean = Pitch_mean
            self.Pitch_stab = gyro_Y
            self.Roll_stab = gyro_X
            self.max_acc_x = max_acc_x
            self.mean_VMG = mean_VMG
            self.speed_consistancy = speed_consistancy
            self.mean_time = mean_time
            self.time_index = time_index
            if self.TWA_mean_abs <= 80:
                self.mode = 'Up'
            elif self.TWA_mean_abs >= 100:
                self.mode = 'Down'
            elif 80 < self.TWA_mean_abs < 100:
                self.mode = 'Reach'
            if TWA_mean <= 0:
                self.tack = 'Port'
            elif TWA_mean > 0:
                self.tack = 'Starbord'
            self.Acc_mean = Acc_mean
            self.start_time = time[indexes[0]]
            self.end_time = time[indexes[-1]]

    phase_length = int(phase_length / dt)
    half_phase_length = int(phase_length / 2)
    man_wand_before = int(man_wand_to_avoid_before / dt)
    man_wand_after = int(man_wand_to_avoid_after / dt)

    perf_phases_list = []

    man_phase_index_list = []

    for man in man_indexes:
        avoid = range(man - man_wand_before, man + man_wand_after + 1)
        man_phase_index_list.extend(avoid)

    i = half_phase_length

    while i <= len(time) - half_phase_length:

        if np.std(TWA[i - half_phase_length: i + half_phase_length + 1]) < std_twa_limit:

            transition = False
            for sp in speed[i - half_phase_length: i + half_phase_length + 1]:
                if sp < 0:
                    transition = True

            indexes = range(i - half_phase_length, i + half_phase_length + 1)
            speed_median = stat.median(speed[i - half_phase_length: i + half_phase_length + 1])

            if not any(x in man_phase_index_list for x in indexes) and speed_median > speed_median_min \
                    and not transition:

                TWA_list = TWA[i - half_phase_length: i + half_phase_length + 1]
                TWA_list_abs = [abs(x) for x in TWA_list]
                TWA_mean_abs = angles_stats(TWA_list_abs, 'Mean')
                TWA_mean = angles_stats(TWA_list, 'Mean')
                Acc_mean = (speed[indexes[-1]] - speed[indexes[0]]) / TimeDelta(time[i - half_phase_length],
                                                                                time[i + half_phase_length])
                Heel_mean = stat.median(
                    abs(x * 180 / math.pi) for x in heel[i - half_phase_length: i + half_phase_length + 1])
                Pitch_mean = stat.median(
                    x * 180 / math.pi for x in pitch[i - half_phase_length: i + half_phase_length + 1])
                mean_VMG = stat.median(VMG[i - half_phase_length: i + half_phase_length + 1])
                speed_consistancy = np.std(speed[i - half_phase_length: i + half_phase_length + 1])

                gyro_y_deg = [x * 180 / math.pi for x in gyro_Y[i - half_phase_length: i + half_phase_length + 1]]
                gyro_x_deg = [x * 180 / math.pi for x in gyro_X[i - half_phase_length: i + half_phase_length + 1]]

                Gyro_Y = np.std(gyro_y_deg)
                Gyro_X = np.std(gyro_x_deg)

                mean_time = time[i]
                time_index = i*10/len(time)

                max_acc_x = max(abs(x) for x in Acc_X[i - half_phase_length: i + half_phase_length + 1])

                if speed_median > 0.4 * stat.median(speed) and abs(Heel_mean) < 90 and abs(Pitch_mean) < 30:
                    new_phase = Phase(indexes, speed_median, TWA_mean_abs, TWA_mean, Acc_mean, Heel_mean, Pitch_mean,
                                      speed_consistancy, Gyro_Y, Gyro_X, max_acc_x, mean_VMG, mean_time, time_index)
                    perf_phases_list.append(new_phase)

                i += phase_length

                continue

        i += 1

    return perf_phases_list

########################################################################################################################


def Analyze_Phases_App(phases):

    SOG_upwind_preclean = []
    SOG_upwind_cut = []
    SOG_downwind_preclean = []

    SOG_port_upwind = []
    SOG_Stbd_upwind = []
    SOG_port_downwind = []
    SOG_Stbd_downwind = []

    TWA_port_upwind = []
    TWA_Stbd_upwind = []
    TWA_port_downwind = []
    TWA_Stbd_downwind = []

    Heel_port_upwind = []
    Heel_Stbd_upwind = []
    Heel_port_downwind = []
    Heel_Stbd_downwind = []

    SOG_consistancy_port_upwind = []
    SOG_consistancy_Stbd_upwind = []
    SOG_consistancy_port_downwind = []
    SOG_consistancy_Stbd_downwind = []

    Pitch_port_upwind = []
    Pitch_Stbd_upwind = []
    Pitch_port_downwind = []
    Pitch_Stbd_downwind = []

    Pitch_stab_port_upwind = []
    Pitch_stab_Stbd_upwind = []
    Pitch_stab_port_downwind = []
    Pitch_stab_Stbd_downwind = []

    Roll_stab_port_upwind = []
    Roll_stab_Stbd_upwind = []
    Roll_stab_port_downwind = []
    Roll_stab_Stbd_downwind = []

    VMG_port_upwind = []
    VMG_Stbd_upwind = []
    VMG_port_downwind = []
    VMG_Stbd_downwind = []

    Stats = {}

    upwind_phases_preclean = [ph for ph in phases if ph.mode == 'Up']

    downwind_phases_preclean = [ph for ph in phases if ph.mode == 'Down']

    for ph in upwind_phases_preclean:
        SOG_upwind_preclean.append(ph.speed_median)

    # maxSOGup=max(SOG_upwind_preclean)
    # minSOGup=min(SOG_upwind_preclean)
    meanup = np.mean(SOG_upwind_preclean)

    upwind_phases_cut = [ph for ph in upwind_phases_preclean if ph.speed_median >= meanup]

    # We now seek the mean of the upper values

    for ph in upwind_phases_cut:
        SOG_upwind_cut.append(ph.speed_median)

    meanupcut = np.mean(SOG_upwind_cut)

    upwind_phases = [ph for ph in upwind_phases_preclean if
                     (ph.speed_median >= 0.8 * meanupcut and ph.speed_median >= 1.2 * meanupcut)]

    for ph in downwind_phases_preclean:
        SOG_downwind_preclean.append(ph.speed_median)

    # maxSOGdown=max(SOG_downwind_preclean)
    # minSOGdown=min(SOG_downwind_preclean)
    meandown = np.mean(SOG_downwind_preclean)

    downwind_phases = [ph for ph in downwind_phases_preclean if ph.speed_median >= meandown]

    port_upwind_phases = [ph for ph in upwind_phases if ph.tack == 'Port']
    starbord_upwind_phases = [ph for ph in upwind_phases if ph.tack == 'Starbord']

    port_downwind_phases = [ph for ph in downwind_phases if ph.tack == 'Port']
    starbord_downwind_phases = [ph for ph in downwind_phases if ph.tack == 'Starbord']

    for ph in port_upwind_phases:
        SOG_port_upwind.append(ph.speed_median)
        TWA_port_upwind.append(ph.TWA_mean_abs)
        Heel_port_upwind.append(ph.Heel_mean)
        SOG_consistancy_port_upwind.append(ph.speed_consistancy)
        Pitch_port_upwind.append(ph.Pitch_mean)
        Pitch_stab_port_upwind.append(ph.Pitch_stab)
        Roll_stab_port_upwind.append(ph.Roll_stab)
        VMG_port_upwind.append(ph.mean_VMG)

    for ph in starbord_upwind_phases:
        SOG_Stbd_upwind.append(ph.speed_median)
        TWA_Stbd_upwind.append(ph.TWA_mean_abs)
        Heel_Stbd_upwind.append(ph.Heel_mean)
        SOG_consistancy_Stbd_upwind.append(ph.speed_consistancy)
        Pitch_Stbd_upwind.append(ph.Pitch_mean)
        Pitch_stab_Stbd_upwind.append(ph.Pitch_stab)
        Roll_stab_Stbd_upwind.append(ph.Roll_stab)
        VMG_Stbd_upwind.append(ph.mean_VMG)

    for ph in port_downwind_phases:
        SOG_port_downwind.append(ph.speed_median)
        TWA_port_downwind.append(ph.TWA_mean_abs)
        Heel_port_downwind.append(ph.Heel_mean)
        SOG_consistancy_port_downwind.append(ph.speed_consistancy)
        Pitch_port_downwind.append(ph.Pitch_mean)
        Pitch_stab_port_downwind.append(ph.Pitch_stab)
        Roll_stab_port_downwind.append(ph.Roll_stab)
        VMG_port_downwind.append(ph.mean_VMG)

    for ph in starbord_downwind_phases:
        SOG_Stbd_downwind.append(ph.speed_median)
        TWA_Stbd_downwind.append(ph.TWA_mean_abs)
        Heel_Stbd_downwind.append(ph.Heel_mean)
        SOG_consistancy_Stbd_downwind.append(ph.speed_consistancy)
        Pitch_Stbd_downwind.append(ph.Pitch_mean)
        Pitch_stab_Stbd_downwind.append(ph.Pitch_stab)
        Roll_stab_Stbd_downwind.append(ph.Roll_stab)
        VMG_Stbd_downwind.append(ph.mean_VMG)

    Stats['SOG_port_upwind_mean'] = np.mean(SOG_port_upwind)
    Stats['SOG_Stbd_upwind_mean'] = np.mean(SOG_Stbd_upwind)
    Stats['SOG_port_downwind_mean'] = np.mean(SOG_port_downwind)
    Stats['SOG_Stbd_downwind_mean'] = np.mean(SOG_Stbd_downwind)
    Stats['TWA_port_upwind'] = np.mean(TWA_port_upwind)
    Stats['TWA_Stbd_upwind'] = np.mean(TWA_Stbd_upwind)
    Stats['TWA_port_downwind'] = np.mean(TWA_port_downwind)
    Stats['TWA_Stbd_downwind'] = np.mean(TWA_Stbd_downwind)
    Stats['Heel_port_upwind'] = np.mean(Heel_port_upwind)
    Stats['Heel_Stbd_upwind'] = np.mean(Heel_Stbd_upwind)
    Stats['Heel_port_downwind'] = np.mean(Heel_port_downwind)
    Stats['Heel_Stbd_downwind'] = np.mean(Heel_Stbd_downwind)
    Stats['SOG_consistancy_port_upwind'] = np.mean(SOG_consistancy_port_upwind)
    Stats['SOG_consistancy_Stbd_upwind'] = np.mean(SOG_consistancy_Stbd_upwind)
    Stats['SOG_consistancy_port_downwind'] = np.mean(SOG_consistancy_port_downwind)
    Stats['SOG_consistancy_Stbd_downwind'] = np.mean(SOG_consistancy_Stbd_downwind)
    Stats['Pitch_port_upwind'] = np.mean(Pitch_port_upwind)
    Stats['Pitch_Stbd_upwind'] = np.mean(Pitch_Stbd_upwind)
    Stats['Pitch_port_downwind'] = np.mean(Pitch_port_downwind)
    Stats['Pitch_Stbd_downwind'] = np.mean(Pitch_Stbd_downwind)
    Stats['Pitch_stab_port_upwind'] = np.mean(Pitch_stab_port_upwind)
    Stats['Pitch_stab_Stbd_upwind'] = np.mean(Pitch_stab_Stbd_upwind)
    Stats['Pitch_stab_port_downwind'] = np.mean(Pitch_stab_port_downwind)
    Stats['Pitch_stab_Stbd_downwind'] = np.mean(Pitch_stab_Stbd_downwind)
    Stats['Roll_stab_port_upwind'] = np.mean(Roll_stab_port_upwind)
    Stats['Roll_stab_Stbd_upwind'] = np.mean(Roll_stab_Stbd_upwind)
    Stats['Roll_stab_port_downwind'] = np.mean(Roll_stab_port_downwind)
    Stats['Roll_stab_Stbd_downwind'] = np.mean(Roll_stab_Stbd_downwind)
    Stats['VMG_port_upwind'] = np.mean(VMG_port_upwind)
    Stats['VMG_Stbd_upwind'] = np.mean(VMG_Stbd_upwind)
    Stats['VMG_port_downwind'] = np.mean(VMG_port_downwind)
    Stats['VMG_Stbd_downwind'] = np.mean(VMG_Stbd_downwind)

    return Stats


def create_phases_GPX_EASY(df, speed, time, dt, TWA, VMG, TWS, COG, SOG, man_indexes, man_wand_to_avoid_before,
                           man_wand_to_avoid_after,
                           phase_length, std_twa_limit, speed_median_min, t_start, t_stop, ang_up, ang_down):
    speed = speed.tolist()
    TWA = TWA.tolist()
    VMG = VMG.tolist()
    TWS = TWS.tolist()
    man_indexes = man_indexes.tolist()
    man_indexes = list(filter(None, man_indexes))

    class Leg(object):
        def __init__(self, legstart, legstop, legmode, race, num, legs, man):
            self.Start = legstart
            self.Stop = legstop
            self.Mode = legmode
            self.Race = race
            self.Number = num
            self.Phases = legs
            self.Manoeuvres = man

    class Phase(object):

        def __init__(self, indexes, speed_median, TWA_mean_abs, TWA_mean, Acc_mean, speed_consistancy, mean_VMG,
                     mean_TWS, mean_COG, mean_SOG, mean_time, time_index):
            self.indexes = indexes
            self.speed_median = speed_median
            self.TWA_mean = TWA_mean
            self.TWA_mean_abs = TWA_mean_abs
            self.speed_consistancy = speed_consistancy
            self.mean_VMG = mean_VMG
            self.mean_TWS = mean_TWS
            self.mean_time = mean_time
            self.mean_SOG = mean_SOG
            self.mean_COG = mean_COG
            self.time_index = time_index
            self.duration = (indexes[-1]-indexes[0])*dt

            if self.TWA_mean_abs <= ang_up:
                self.mode = 'Up'
                self.m='U'
            elif self.TWA_mean_abs > ang_down:
                self.mode = 'Down'
                self.m='D'
            elif ang_up <= self.TWA_mean_abs <= ang_down:
                self.mode = 'Reach'
                self.m='O'
            if TWA_mean <= 0:
                self.tack = 'Port'
                self.t='P'
            elif TWA_mean > 0:
                self.tack = 'Starbord'
                self.t='S'
            self.Acc_mean = Acc_mean
            self.start_time = time[indexes[0]]
            self.end_time = time[indexes[-1]]

        def to_DF(self):

            return {
                'TWA': self.TWA_mean,
                'DurationSec': self.duration,
                'SailingMode': self.m,
                'Tack': self.t,
                'TWA': self.TWA_mean_abs,
                'TWS': self.mean_TWS,
                'VMG': self.mean_VMG,
                'BSP': self.mean_SOG,
                'COG': self.mean_COG,
                'StartTime': self.start_time

            }

    phase_length = int(phase_length / dt)
    half_phase_length = int(phase_length / 2)
    man_wand_before = int(man_wand_to_avoid_before / dt)
    man_wand_after = int(man_wand_to_avoid_after / dt)

    perf_phases_list = []
    perf_legs_list = []

    man_phase_index_list = []

    legstart=0
    ph=1

    for man in man_indexes:
        avoid = range(man - man_wand_before, man + man_wand_after + 1)
        man_phase_index_list.extend(avoid)

    i = df.index[df['Date_Time'] == t_start].tolist()[0] + half_phase_length
    i_stop = df.index[df['Date_Time'] == t_stop].tolist()[0] - half_phase_length

    while i <= i_stop:
        hu = circstd(pd.Series(TWA[i - half_phase_length: i + half_phase_length + 1]) * np.pi / 180)
        if hu < std_twa_limit:

            transition = False
            for sp in speed[i - half_phase_length: i + half_phase_length + 1]:
                if sp < 0:
                    transition = True

            indexes = range(i - half_phase_length, i + half_phase_length + 1)
            speed_median = stat.median(speed[i - half_phase_length: i + half_phase_length + 1])

            if not any(x in man_phase_index_list for x in indexes) and speed_median > speed_median_min \
                    and not transition:
                TWA_list = TWA[i - half_phase_length: i + half_phase_length + 1]
                TWA_list_abs = [abs(x) for x in TWA_list]
                TWA_mean_abs = angles_stats(TWA_list_abs, 'Mean', twa=True)
                TWA_mean = angles_stats(TWA_list, 'Mean', twa=True)
                Acc_mean = (speed[indexes[-1]] - speed[indexes[0]]) / TimeDelta(time[i - half_phase_length],
                                                                                time[i + half_phase_length])
                speed_consistancy = np.std(speed[i - half_phase_length: i + half_phase_length + 1])
                mean_VMG = stat.median(VMG[i - half_phase_length: i + half_phase_length + 1])
                mean_SOG = stat.median(SOG[i - half_phase_length: i + half_phase_length + 1])
                mean_COG = stat.median(COG[i - half_phase_length: i + half_phase_length + 1])
                mean_TWS = stat.median(TWS[i - half_phase_length: i + half_phase_length + 1])
                mean_time = time[i]
                time_index = i*10/len(time)

                new_phase = Phase(indexes, speed_median, TWA_mean_abs, TWA_mean, Acc_mean, speed_consistancy, mean_VMG,
                                  mean_TWS, mean_COG, mean_SOG, mean_time, time_index)

                if perf_phases_list!=[]:
                    if (new_phase.mode != perf_phases_list[-1].mode):
                        ph += 1
                        legpoint=[manu for manu in man_indexes if (manu >= perf_phases_list[-1].indexes[-1] and manu <= new_phase.indexes[0])]
                        legmode=perf_phases_list[-1].mode
                        if legpoint==[]:
                            legstop = perf_phases_list[-1].indexes[-1]
                            perf_legs_list.append(Leg(legstart, legstop, legmode, 0, 0, ph, 0))
                            legstart=new_phase.indexes[0]

                        else:
                            legstop = legpoint[0]
                            perf_legs_list.append(Leg(legstart, legstop, legmode, 0, 0, ph, 0))
                            legstart= legpoint[0]

                        ph = 0

                    else:
                        ph+=1

                perf_phases_list.append(new_phase)

                i += phase_length

                continue

        i += 1


    legstop=len(speed)
    legmode=perf_phases_list[-1].mode
    perf_legs_list.append(Leg(legstart, legstop, legmode, 0, 0, 0, 0))

    return perf_phases_list, perf_legs_list


def Analyze_Phases_GPX_EASY(phases, treshold):

    SOG_port_upwind = []
    SOG_Stbd_upwind = []
    SOG_port_downwind = []
    SOG_Stbd_downwind = []

    TWA_port_upwind = []
    TWA_Stbd_upwind = []
    TWA_port_downwind = []
    TWA_Stbd_downwind = []

    SOG_consistancy_port_upwind = []
    SOG_consistancy_Stbd_upwind = []
    SOG_consistancy_port_downwind = []
    SOG_consistancy_Stbd_downwind = []

    VMG_port_upwind = []
    VMG_Stbd_upwind = []
    VMG_port_downwind = []
    VMG_Stbd_downwind = []

    Stats = {}

    [upwind_phases,downwind_phases] = phaseclean(phases, treshold)

    port_upwind_phases = [ph for ph in upwind_phases if ph.tack == 'Port']
    starbord_upwind_phases = [ph for ph in upwind_phases if ph.tack == 'Starbord']

    port_downwind_phases = [ph for ph in downwind_phases if ph.tack == 'Port']
    starbord_downwind_phases = [ph for ph in downwind_phases if ph.tack == 'Starbord']

    for ph in port_upwind_phases:
        SOG_port_upwind.append(ph.speed_median)
        TWA_port_upwind.append(ph.TWA_mean_abs)
        SOG_consistancy_port_upwind.append(ph.speed_consistancy)
        VMG_port_upwind.append(ph.mean_VMG)

    for ph in starbord_upwind_phases:
        SOG_Stbd_upwind.append(ph.speed_median)
        TWA_Stbd_upwind.append(ph.TWA_mean_abs)
        SOG_consistancy_Stbd_upwind.append(ph.speed_consistancy)
        VMG_Stbd_upwind.append(ph.mean_VMG)

    for ph in port_downwind_phases:
        SOG_port_downwind.append(ph.speed_median)
        TWA_port_downwind.append(ph.TWA_mean_abs)
        SOG_consistancy_port_downwind.append(ph.speed_consistancy)
        VMG_port_downwind.append(ph.mean_VMG)

    for ph in starbord_downwind_phases:
        SOG_Stbd_downwind.append(ph.speed_median)
        TWA_Stbd_downwind.append(ph.TWA_mean_abs)
        SOG_consistancy_Stbd_downwind.append(ph.speed_consistancy)
        VMG_Stbd_downwind.append(ph.mean_VMG)

    Stats['SOG_port_upwind_mean'] = np.mean(SOG_port_upwind)
    Stats['SOG_Stbd_upwind_mean'] = np.mean(SOG_Stbd_upwind)
    Stats['SOG_port_downwind_mean'] = np.mean(SOG_port_downwind)
    Stats['SOG_Stbd_downwind_mean'] = np.mean(SOG_Stbd_downwind)
    Stats['TWA_port_upwind'] = np.mean(TWA_port_upwind)
    Stats['TWA_Stbd_upwind'] = np.mean(TWA_Stbd_upwind)
    Stats['TWA_port_downwind'] = np.mean(TWA_port_downwind)
    Stats['TWA_Stbd_downwind'] = np.mean(TWA_Stbd_downwind)
    Stats['SOG_consistancy_port_upwind'] = np.mean(SOG_consistancy_port_upwind)
    Stats['SOG_consistancy_Stbd_upwind'] = np.mean(SOG_consistancy_Stbd_upwind)
    Stats['SOG_consistancy_port_downwind'] = np.mean(SOG_consistancy_port_downwind)
    Stats['SOG_consistancy_Stbd_downwind'] = np.mean(SOG_consistancy_Stbd_downwind)
    Stats['VMG_port_upwind'] = np.mean(VMG_port_upwind)
    Stats['VMG_Stbd_upwind'] = np.mean(VMG_Stbd_upwind)
    Stats['VMG_port_downwind'] = np.mean(VMG_port_downwind)
    Stats['VMG_Stbd_downwind'] = np.mean(VMG_Stbd_downwind)

    return Stats, upwind_phases, port_upwind_phases, starbord_upwind_phases, downwind_phases, port_downwind_phases,\
           starbord_downwind_phases


#######################################################################################################################


def Tack_Gybe_Analysis_App(tacking_indexes, gybing_indexes, Time, SOG, TWA, AccZ, Altitude, GyroY, dt, time_before,
                           time_after):
    class Tack(object):

        def __init__(self, index, speed, twa, gyro_Y, acc_Z, altitude, time_to_50):
            self.index = index
            self.speed = speed
            self.TWA = twa
            self.time_to_50 = time_to_50
            self.Gyro_Y = gyro_Y
            self.Acc_Z = acc_Z
            self.Altitude = altitude
            self.SOG_before = self.speed[0]
            self.SOG_after = self.speed[-1]
            self.TWA_before = self.TWA[0]
            self.TWA_after = self.TWA[-1]
            self.min_SOG = min(self.speed)
            self.median_SOG = stat.median(self.speed)

    class Gybe(object):

        def __init__(self, index, speed, twa, gyro_Y, acc_Z, altitude):
            self.index = index
            self.speed = speed
            self.TWA = twa
            self.Gyro_Y = gyro_Y
            self.Acc_Z = acc_Z
            self.Altitude = altitude

    wand_index_before = int(time_before / dt)
    wand_index_after = int(time_after / dt)

    SOG = SOG.tolist()
    TWA = TWA.tolist()
    AccZ = AccZ.tolist()
    GyroY = GyroY.tolist()
    Altitude = Altitude.tolist()
    Time = Time.tolist()

    tack_list = []
    gybe_list = []

    for i in tacking_indexes:
        speed = SOG[i - wand_index_before: i + wand_index_after + 1]
        twa = TWA[i - wand_index_before: i + wand_index_after + 1]
        acc_Z = AccZ[i - wand_index_before: i + wand_index_after + 1]
        gyro_Y = GyroY[i - wand_index_before: i + wand_index_after + 1]
        altitude = Altitude[i - wand_index_before: i + wand_index_after + 1]
        time = Time[i - wand_index_before: i + wand_index_after + 1]

        speed_mean_before = SOG[i - wand_index_before]
        aim_speed = speed_mean_before * 0.5

        # for

        tack = Tack(i, speed, twa, gyro_Y, acc_Z, altitude)

        tack_list.append(tack)

    for i in gybing_indexes:
        speed = SOG[i - wand_index_before: i + wand_index_after + 1]
        twa = TWA[i - wand_index_before: i + wand_index_after + 1]
        acc_Z = AccZ[i - wand_index_before: i + wand_index_after + 1]
        gyro_Y = GyroY[i - wand_index_before: i + wand_index_after + 1]
        altitude = Altitude[i - wand_index_before: i + wand_index_after + 1]
        time = Time[i - wand_index_before: i + wand_index_after + 1]

        gybe = Gybe(i, speed, twa, gyro_Y, acc_Z, altitude)

        gybe_list.append(gybe)


def Tack_Gybe_Analysis_GPX_EASY(tacking_indexes, gybing_indexes, Time, SOG, TWA, dt, time_before, time_after_1,
                                time_after_2):
    class Tack(object):

        def __init__(self, index, time, SOG_10_after, speed, twa, TWA_10_after, time_to_80):
            self.index = index
            self.time = time
            self.speed = speed
            self.TWA = twa
            self.time_to_80 = time_to_80
            self.SOG_10s_after = SOG_10_after
            self.SOG_20s_after = speed[-1]
            self.SOG_5s_before = speed[0]
            self.TWA_5s_before = twa[0]
            self.TWA_10s_after = TWA_10_after
            self.TWA_20s_after = twa[-1]
            self.min_SOG = min(speed)
            self.median_SOG = stat.median(speed)

    class Gybe(object):

        def __init__(self, index, time, SOG_10_after, speed, twa, TWA_10_after, time_to_80):
            self.index = index
            self.time = time
            self.speed = speed
            self.TWA = twa
            self.time_to_80 = time_to_80
            self.SOG_10s_after = SOG_10_after
            self.SOG_20s_after = speed[-1]
            self.SOG_5s_before = speed[0]
            self.TWA_5s_before = twa[0]
            self.TWA_10s_after = TWA_10_after
            self.TWA_20s_after = twa[-1]
            self.min_SOG = min(speed)
            self.median_SOG = stat.median(speed)

    wand_index_before = int(time_before / dt)
    wand_index_after_1 = int(time_after_1 / dt)
    wand_index_after_2 = int(time_after_2 / dt)

    SOG = SOG.tolist()
    TWA = TWA.tolist()
    Time = Time.tolist()

    tacking_indexes = list(filter(None, tacking_indexes))
    gybing_indexes = list(filter(None, gybing_indexes))

    tack_list = []
    gybe_list = []

    for i in tacking_indexes:

        speed = SOG[i - wand_index_before: i + wand_index_after_2 + 1]
        twa = TWA[i - wand_index_before: i + wand_index_after_2 + 1]
        time = Time[i]

        speed_mean_before = stat.median(SOG[i - int(30 / dt): i - wand_index_before])
        aim_speed = speed_mean_before * 0.8

        j = i

        while SOG[j] < aim_speed:
            j += 1

        time_to_80 = TimeDelta(Time[i], Time[j])

        print(Time[i], 'SOG at Tack:', SOG[i], 'aim_speed: ', aim_speed, 'Time_to_50: ', time_to_80)

        tack = Tack(i, time, SOG[i + wand_index_after_1], speed, twa, TWA[i + wand_index_after_1], time_to_80)

        tack_list.append(tack)

    for i in gybing_indexes:

        speed = SOG[i - wand_index_before: i + wand_index_after_2 + 1]
        twa = TWA[i - wand_index_before: i + wand_index_after_2 + 1]
        time = Time[i]

        speed_mean_before = stat.median(SOG[i - int(30 / dt): i - wand_index_before])
        aim_speed = speed_mean_before * 0.8

        j = i

        while SOG[j] < aim_speed:
            j += 1

        time_to_80 = TimeDelta(Time[i], Time[j])

        gybe = Gybe(i, time, SOG[i + wand_index_after_1], speed, twa, TWA[i + wand_index_after_1], time_to_80)

        gybe_list.append(gybe)

    return tack_list, gybe_list


#####################################################################################################################


def timeindextodate(indexes, time):

    dates=pd.date_range(start=time[int(indexes[0]*len(time)/10)], end=time[int(indexes[-1]*len(time)/10)], periods=(len(indexes))).tolist()

    return dates


def datetoindex(date,log,dt):
    # index = int(len(log))-len(pd.date_range(start=date, end=log.Date_Time[len(log)-1], freq=(str(int(dt))+'s')))
    index = log[log.Date_Time == date].index.asi8[0]
    return index


def log_export_mod(log, params, AnalyzedLegs, dec):

    cols = list(log.columns)

    if 'BSP' in cols:
        del log['BSP']

    if 'Date' in cols:
        del log['Date']

    if 'Time' in cols:
        del log['Time']

    log = log.rename({'Latitude': 'GpsLat', 'Longitude': 'GpsLon', 'Date_Time':'Time', 'SOG_Kts':'BSP'}, axis=1)
    log['BoatName'] = params['Name']
    log['BoatName_col'] = params['Name_color']
    [log['Tack'], log['SailingMode']] = TackMode(log, params['Upwind_Reach_Angle'], params['Downwind_Reach_Angle'])
    [log['RaceLeg'], log['RaceLeg_col']] = LegLog(log, AnalyzedLegs, params['race_mode'])

    log['TWA'] = abs(log['TWA'])
    log['TWS_col'] = color_scale(log['TWS'])
    log['BSP_col'] = color_scale(log['BSP'])
    log['SailsUp'] = 'Sails'
    log['SailsUp_col'] = params['Name_color']
    log['End'] = 'End'
    glat = round(log.GpsLat,6)
    glon = round(log.GpsLon,6)

    if ('DB_RAKE_S' in cols and 'LENGTH_RH_P' in cols):
        rh=[]
        rake_p=[]
        rake_s=[]
        for i in range(len(log.TWA)):
            if log.TWA[i]>0:
                rh.append(log.LENGTH_RH_P[i])
            else:
                rh.append(log.LENGTH_RH_S[i])

            if log.DB_RAKE_P[i]>1:
                rake_p.append('red')
            else:
                rake_p.append('white')

            if log.DB_RAKE_S[i]>1:
                rake_s.append('#00FF00')
            else:
                rake_s.append('white')

        log['RH_LEE']=rh
        log['DB_RAKE_P_col'] = rake_p
        log['DB_RAKE_S_col'] = rake_s

    if 'LENGTH_DB_H_P' in cols:
        cscheme = colour_scheme_reader('Input/colorschemes/ColourSchemes.xml')

        log['LENGTH_DB_H_P_col'] = color_scale(log['LENGTH_DB_H_P'], [mf.bgr_to_hex(color) for color in
                                                                      cscheme['LENGTH_DB_H_P']['colourmaps']['colour']],
                                               cscheme['LENGTH_DB_H_P']['colourmaps']['value'][1:])
        log['LENGTH_DB_H_S_col'] = color_scale(log['LENGTH_DB_H_S'], [mf.bgr_to_hex(color) for color in
                                                                      cscheme['LENGTH_DB_H_S']['colourmaps']['colour']],
                                               cscheme['LENGTH_DB_H_S']['colourmaps']['value'][1:])

    log = round(log, dec)
    log['GpsLat'] = glat
    log['GpsLon'] = glon


    return log


def phaselog_mod(plog, params, targets, log, AnalyzedPhases, pleglog, pcolorlog, dec):

    del log['SailsUp']
    del log['End']

    plog['BoatName'] = params['Name']
    plog['BoatName_col'] = params['Name_color']
    [plog['RaceLeg'], plog['RaceLeg_col']] = [pleglog, pcolorlog]

    plog['TWS_bin'] = 2 * round(plog['TWS'] / 2)
    plog['TWS_bin_col'] = color_scale(plog['TWS_bin'])
    if targets!={}:
        plog['ΔBspTrg'] = delta_builder(plog['SailingMode'], plog['BSP'], plog['TWS'], targets['UpBsp'] , targets['DnBsp'])[0]
        plog['ΔTwaTrg'] = delta_builder(plog['SailingMode'], plog['TWA'], plog['TWS'], targets['UpTwa'], targets['DnTwa'])[0]
        [plog['ΔVmgTrg'], plog['VMG_trg%'], plog['ΔVmgTrg%']] = delta_builder(plog['SailingMode'], plog['VMG'], plog['VMG'],
                                                                      targets['VMGvsTWS_UP'] , targets['VMGvsTWS_DOWN'])

    cols = [c for c in log.columns if (type(log[c][1])!=str and 'Time' not in c)]
    pcols = list(plog.columns)
    for phase in AnalyzedPhases:
        for col in cols:
            if col not in pcols:
                plog[col] = np.mean(log[col][phase.indexes[0]:phase.indexes[1]])

    if ('DB_RAKE_S' in cols and 'LENGTH_RH_P' in pcols):
        rh=[]
        rake_p=[]
        rake_s=[]
        for i in range(len(plog.TWA)):
            if plog.TWA[i]>0:
                rh.append(plog.LENGTH_RH_P[i])
            else:
                rh.append(plog.LENGTH_RH_S[i])

            if plog.DB_RAKE_P[i]>1:
                rake_p.append('red')
            else:
                rake_p.append('white')

            if plog.DB_RAKE_S[i]>1:
                rake_s.append('#00FF00')
            else:
                rake_s.append('white')

        plog['RH_LEE']=rh
        plog['DB_RAKE_P_col'] = rake_p
        plog['DB_RAKE_S_col'] = rake_s

    plog['End'] = 'End'
    plog=round(plog, dec)

    return plog


def colour_scheme_reader(path):
    """
    :param path: path of the preset file
    :return: dictionnary with all settings
    """
    tree = ET.parse(path)
    root = tree.getroot()
    dictionary = defaultdict(dict)
    dictionary['graph_type'] = "colour_scheme"
    for child in root:
        for item in child:
            key = item.get('name')
            dictionary[key] = defaultdict(dict)
            dictionary[key]['name'] = item.get('name')
            dictionary[key]['variablename'] = item.get('variablename')
            dictionary[key]['minvalue'] = item.get('minvalue')
            dictionary[key]['mincol'] = item.get('mincol')
            dictionary[key]['maxvalue'] = item.get('maxvalue')
            dictionary[key]['maxcol'] = item.get('maxcol')
            dictionary[key]['interpolate'] = item.get('interpolate')
            dictionary[key]['colourmaps']['value'] = []
            dictionary[key]['colourmaps']['colour'] = []
            for colourmaps in item:
                for item2 in colourmaps:
                    dictionary[key]['colourmaps']['value'].append(item2.get('value'))
                    dictionary[key]['colourmaps']['colour'].append(item2.get('colour'))
            dictionary[key]['colourmaps']['value'].append(dictionary[key]['maxvalue'])
            dictionary[key]['colourmaps']['colour'].append(dictionary[key]['maxcol'])
            dictionary[key]['colourmaps']['value'].insert(0, dictionary[key]['minvalue'])
            dictionary[key]['colourmaps']['colour'].insert(0, dictionary[key]['mincol'])
    return dictionary


def trygui():
    for i in range(0,100000000):
        a=1