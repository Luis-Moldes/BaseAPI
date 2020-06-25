import requests
import snippets.Warp10Util
import json
import pandas as pd
import numpy as np
import statistics as stat
from rest_framework import exceptions
import snippets.Warp_Config as conf
from snippets.Tools import angles_stats
from snippets.RememberTime_API import RememberTime
from snippets.functions_API import calculate_TWA, datetoindex, manoeuvres_gpx_easy_API, sliding_log
import time as tyme
#
# def WarpRetrieve(boat_id, event_id, start_time, stop_time, twd, tws, upwind_angle, downwind_angle, tack_wand, gybe_wand,
#                  speedovec, speed_treshold_perc):
def WarpRetrieve(boat_id, event_id, filter, config):

        url=conf.warp_url

        variables = conf.vars
        variables_bucket = conf.bucket_vars

        warnings=[]

        # Checking how complete the dict is isn't easy, there might be a whole field or just a variable missing

        filter_vars=['start_time','stop_time','only_while_sailing']

        if filter==None: #If the whole field is missing
                filter={}
                for i in filter_vars: #You have to create the variables and set them all to None
                        filter[i]=None
        else: #If the field is there you still have to check that all te variables are there
                for i in filter_vars:
                        if i not in filter.keys(): #If one of them isn't, you create it and set it to None
                                filter[i]=None

        config_vars=['twd_if_missing','tws_if_missing','upwind_angle', 'downwind_angle', 'tack_detection', 'gybe_detection', 'speedo_calibration']

        if config==None:
                config={}
                for i in config_vars:
                        config[i]=None
        else:
                for i in config_vars:
                        if i not in config.keys():
                                config[i]=None

        man_vars = ['time_before','time_after', 'avg_time', 'speed_threshold_pctg'] #You also must check fields that have in turn other felds

        for manny in ['tack_detection', 'gybe_detection']:
                if config[manny]==None:
                        config[manny]={}
                        for i in man_vars:
                                config[manny][i]=None
                else:
                        for i in man_vars:
                                if i not in config[manny].keys():
                                        config[manny][i]=None

        #Then you apply the corresponding criteria to each variable


        ''' CONFIG '''

        if config['upwind_angle']==None:
                upwind_angle=80
                warnings.append('- No upwind reaching wind angle found in input, it will be set to 80º')
        else:
                upwind_angle = float(config['upwind_angle'])

        if config['downwind_angle']==None:
                downwind_angle=110
                warnings.append('- No downwind reaching wind angle found in input, it will be set to 110º')
        else:
                downwind_angle = float(config['downwind_angle'])

        if config['speedo_calibration'] == None:
                speedovec = [5,8]
                warnings.append('- No values for speedometer calibration steps found in input, default values will be used [5,8]')
        else:
                speedovec = eval(config['speedo_calibration'])



        ''' MANEUVER DETECTION '''

        if None in [config['tack_detection']['time_before'],config['tack_detection']['time_after'],config['tack_detection']['avg_time']]:
                tack_wand=[20,40,15] #Time before, after, average
                warnings.append('- Missing parameters for tack analysis wand found in input, default values will be used')
        else:
                tack_wand=[int(i) for i in [config['tack_detection']['time_before'],config['tack_detection']['time_after'],
                                            config['tack_detection']['avg_time']]]

        if config['tack_detection']['speed_threshold_pctg'] == None:
                speed_treshold_perc_tack = 0.7
                warnings.append('- No speed threshold percentage for tack selection found in input, it will be set to 85% of the mean SOG')
        else:
                speed_treshold_perc_tack=float(config['tack_detection']['speed_threshold_pctg'])

        if None in [config['gybe_detection']['time_before'],config['gybe_detection']['time_after'],config['gybe_detection']['avg_time']]:
                gybe_wand=[30,60,15] #Time before, after, average
                warnings.append('- Missing parameters for tack analysis wand found in input, default values will be used')
        else:
                gybe_wand=[int(i) for i in [config['gybe_detection']['time_before'],config['gybe_detection']['time_after'],
                                            config['gybe_detection']['avg_time']]]

        if config['gybe_detection']['speed_threshold_pctg'] == None:
                speed_treshold_perc_gybe = 0.7
                warnings.append('- No speed threshold percentage for gybe selection found in input, it will be set to 85% of the mean SOG')
        else:
                speed_treshold_perc_gybe=float(config['gybe_detection']['speed_threshold_pctg'])



        ''' FILTER '''

        if filter['start_time']==None or filter['stop_time']==None:
                start_str = '2015-05-16T15:00:00.000Z'
                stop_str = '2100-05-16T17:00:10.000Z'
                warnings.append('- No analysis times found in input')
        else:
                start_str = filter['start_time'][:10] + 'T' + filter['start_time'][-8:] + '.000Z'
                stop_str = filter['stop_time'][:10] + 'T' + filter['stop_time'][-8:] + '.000Z'

        if filter['only_while_sailing']==None or filter['only_while_sailing']=='False':
                need_times='F'
                if filter['start_time'] == None or filter['stop_time'] == None:
                        warnings.append('- Consider setting \'only_while_sailing\' to True for a more precise analysis')
        else:
                need_times='T'

        tmps0 = tyme.perf_counter()

        script= r"'"+conf.warp_token+"'"   + "\n" \
                r"'Rt' STORE" + "\n" \
                r"$Rt AUTHENTICATE 1000000 LIMIT 1000000 MAXOPS 10000 MAXLOOP"  + "\n" \
                r"'"+start_str+"' 'start' STORE"  + "\n" \
                r"'"+stop_str+"' 'stop' STORE"  + "\n" \
                r"[ $Rt '" + conf.name + "' { 'boat_id' '"+boat_id+"' 'event_id' '"+event_id+"' } $start $stop ] FETCH  0 GET 'BoatData' STORE"  + "\n" \
                r"$BoatData"  + "\n" \
                r"MVINDEXSPLIT { 'DOUBLE' '~.*{}' } ->GTS"  + "\n" \
                r"'input' STORE"  + "\n" \
                r"<% 2 DROPN 4 REMOVE DROP [ NaN ] APPEND 3 ROLLD 2 DROPN %> 'NANFILLER' STORE" + "\n" \
                r"" + need_times + "" + "\n" \
                r"<%" + "\n" \
                r"<%" + "\n" \
                r"[ $Rt 'boat.status' { 'boat_id' '" + boat_id + "' 'event_id' '" + event_id + "' } $start $stop ] FETCH 0 GET 'status' STORE" + "\n" \
                r"[ $status bucketizer.last 0 1 s 0 ] BUCKETIZE 0 GET" + "\n" \
                r"FILLPREVIOUS" + "\n" \
                r"[ SWAP 'sailing' mapper.eq 0 0 0 ] MAP 0 GET 'sailticks' STORE" + "\n" \
                r"[ $BoatData $sailticks ] COMMONTICKS 0 GET 'BoatData' STORE" + "\n"\
                r"2 'mode' STORE" + "\n" \
                r"%>" + "\n" \
                r"<%" + "\n" \
                r"1 'mode' STORE" + "\n" \
                r"%>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"%>" + "\n" \
                r"<%" + "\n" \
                r"0 'mode' STORE" + "\n" \
                r"%>" + "\n" \
                r"IFTE" + "\n" \
                r"$input 1 GET 'sog_nogap' STORE" + "\n" \
                r"$input 0 GET 'cog' STORE"  + "\n" \
                r"$input 1 GET 'sog' STORE" + "\n" \
                r"[ $input 0 GET 360 bucketizer.mean.circular 0 60 s 0 ] BUCKETIZE 0 GET VALUES 'cog1min' STORE" + "\n" \
                r"[ $input 1 GET bucketizer.mean 0 60 s 0 ] BUCKETIZE 0 GET VALUES 'sog1min' STORE" + "\n" \
                r"<% $input 2 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT 'hdg' STORE" + "\n" \
                r"[ [ [ $cog $hdg ] [] op.sub ] APPLY mapper.abs 0 0 0 ] MAP 0 GET VALUES 'DeltaCOG' STORE" + "\n" \
                r"$hdg VALUES 'hdg' STORE %>" + "\n" \
                r"<% [] 'hdg' STORE" + "\n" \
                r"[] 'DeltaCOG' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 3 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT 'stw' STORE" + "\n" \
                r"[ [ [ $sog $stw ] [] op.sub ] APPLY mapper.abs 0 0 0 ] MAP 0 GET VALUES 'DeltaSOG' STORE" + "\n" \
                r"$stw VALUES 'stw' STORE %>" + "\n" \
                r"<% [] 'stw' STORE [] 'DeltaSOG' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 4 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'twd' STORE" + "\n" \
                r"[ $input 4 GET 360 bucketizer.mean.circular 0 60 s 0 ] BUCKETIZE 0 GET VALUES 'twd1min' STORE %>" + "\n" \
                r"<% [] 'twd' STORE [] 'twd1min' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 5 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'tws' STORE " + "\n" \
                r"[ $input 5 GET bucketizer.mean 0 60 s 0 ] BUCKETIZE 0 GET VALUES 'tws1min' STORE %>" + "\n" \
                r"<% [] 'tws' STORE [] 'tws1min' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 6 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'twa' STORE " + "\n" \
                r"[ $input 6 GET bucketizer.mean 0 60 s 0 ] BUCKETIZE 0 GET VALUES 'twa1min' STORE %>" + "\n" \
                r"<% [] 'twa' STORE [] 'twa1min' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 7 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'aws' STORE %>" + "\n" \
                r"<% [] 'aws' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 8 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'awa' STORE %>" + "\n" \
                r"<% [] 'awa' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 9 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'stw_eff' STORE %>" + "\n" \
                r"<% [] 'stw_eff' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"$cog TICKS 'ticks' STORE"  + "\n" \
                r"$cog LOCATIONS 2 ->LIST 'locations' STORE"  + "\n" \
                r"$cog VALUES 'cog' STORE "  + "\n" \
                r"$sog VALUES 'sog' STORE " + "\n" \
                r"$locations 0 GET 'latitudes' STORE"  + "\n" \
                r"$locations 1 GET 'longitudes' STORE"  + "\n" \
                r"[ $ticks $latitudes $longitudes $cog $sog $hdg $stw $twd $tws $twa $aws $awa $stw_eff $DeltaCOG $DeltaSOG $mode ]" + "\n" \
                r"[ $cog1min $sog1min $twd1min $tws1min $twa1min ]" + "\n"


        header = {"content-type": "application/text"}
        url += "/exec"
        print("Exec script from warp10... " + url)
        r = requests.post(url, headers=header, data=script)
        if (r.status_code!=200):
            raise exceptions.NotAcceptable("ERROR: warp10 server returned statuscode " + str(r.status_code)+ ', ' + str(r.content))
            print("ERROR: warp10 server returned statuscode " + str(r.status_code))
            print(str(r.content))
            exit()

        res=json.loads(r.content) # convert returned string ([[[1558101600000000, 1558101601000000, 1558101602000000, 1558101603000000, 1558101604000000...) to a list
        print("Total time of Warp10 script: ", (tyme.perf_counter() - tmps0))
        res1min=res[0]
        res=res[1]
        # build dataframe
        log = pd.DataFrame({'Date_Time':res[0],
                            'Latitude':res[1],
                            'Longitude':res[2]})
        log['Date_Time']= log['Date_Time'].map(lambda ts: snippets.Warp10Util.EpochToTime(int(ts)))
        for i in range(len(variables)):
                var = variables[i]
                if len(res[i+3])!=0:
                        log[var]=res[i+3]  # may contain some nan! can be tested with np.isnan()

        log1min=pd.DataFrame()
        for i in range(len(variables_bucket)):
                var = variables_bucket[i]
                if len(res1min[i])!=0:
                        log1min[var]=res1min[i]

        log5min = sliding_log(log1min, 2)
        log60min = sliding_log(log1min, 30)

################################################################################################################################
        # log=log.rename(columns={"timestamp": "Date_Time", "lat": "Latitude", "lon": "Longitude", "SOG": "SOG_Kts"})
        dt = stat.mode([log.Date_Time[i + 1] - log.Date_Time[i] for i in range(10)]).seconds #gaps have to be corrected in warp

        # day = log.Date_Time[0]._date_repr

        def to180(i):
                if abs(i) < 180:
                        return(i)
                else:
                        if i>0:
                                return(i-360)
                        else:
                                return (i + 360)

        def to360(i):
                if i < 0:
                        return(i + 360)
                elif i>360:
                        return (i - 360)
                else:
                        return i

        # if need_times=='T':
        #         if res[-1]==[0]:
        #                 warnings+='- No info about sailing modes found in database'
        #                 # start_ind = datetoindex(pd.to_datetime(day+' '+start_time),log,dt)
        #                 # stop_ind = datetoindex(pd.to_datetime(day+' '+stop_time),log,dt)
        #                 start_ind = datetoindex(pd.to_datetime(start_time),log,dt)
        #                 stop_ind = datetoindex(pd.to_datetime(stop_time),log,dt)
        #         else:
        #                 modes=res[-2]
        #                 times=[snippets.Warp10Util.EpochToTime(int(ts)) for ts in res[-1]]
        #                 start_ind = 1
        #                 stop_ind = 1

        if res[-1] == 1:
                warnings.append('- No info about sailing modes found in database: data will be extracted from the whole database')
        elif res[-1] == 2:
                warnings.append('- Sailing modes info was found in database!')

        #TIME REDUCTION

        if 'TWD' not in log.columns:
                if config['twd_if_missing'] is None:
                        log['TWD'] = RememberTime(log)
                        log['TWS'] = pd.Series(np.ones(len(log)) * 10)
                        warnings.append('- No info about wind found in database or input, it will be estimated')
                else:
                        log['TWD'] = pd.Series(np.ones(len(log)) * float(config['twd_if_missing']))
                        log['TWS'] = pd.Series(np.ones(len(log)) * float(config['tws_if_missing']))

                twdmean = log['TWD'][0]
                twsmean = log['TWS'][0]
                log5min['TWD'] = log['TWD'][0]
                log5min['TWS'] = log['TWS'][0]
                log60min['TWD'] = log['TWD'][0]
                log60min['TWS'] = log['TWS'][0]

                twd_left= [log['TWD'][0]]*3
                twd_right = twd_left
                twsmax= [log['TWS'][0]]*3
                twsmin = [log['TWS'][0]] * 3

        else:
                from scipy import stats
                twd_left= []
                twd_right = []
                twsmax= []
                twsmin = []
                twdmean = stats.circmean(log.TWD, high=360)
                twsmean = np.mean(log.TWS)
                # twd5min=log.TWD.rolling(int(min(300 / dt, len(log)))).mean()
                for ilog in [log, log5min, log60min]:
                        twd_left.append(to360(np.nanmin([to180(i-twdmean) for i in ilog.TWD])+twdmean))
                        twd_right.append(to360(np.nanmax([to180(i-twdmean) for i in ilog.TWD])+twdmean))

                        twsmax.append(np.nanmax(ilog.TWS))
                        twsmin.append(np.nanmin(ilog.TWS))

        if 'TWA' not in log.columns:
                log['TWA'] = calculate_TWA(log.Date_Time, log.TWD, log.COG)
                log5min['TWA'] = calculate_TWA(log5min.Date_Time, log5min.TWD, log5min.COG)
                log60min['TWA'] = calculate_TWA(log60min.Date_Time, log60min.TWD, log60min.COG)
        else:
                log['TWA'] = [to180(i) for i in log['TWA']]

        if 'DeltaCOG' in log.columns:
                log['DeltaCOG'] = [abs(to180(i)) for i in log['DeltaCOG']]

        log['Dist'] = log['SOG_Kts'] * dt * 1852 / (3600)

        ########################################## HERE ####################################################
        out={}
        out['SOG']={}
        out['Times'] = {}
        out['Distances'] = {}
        out['TWA'] = {}
        out['TWD'] = {}
        out['TWS'] = {}
        out['Maneuvers'] = {}
        out['Compass_Accuracy'] = {}
        out['Speedometer_Accuracy'] = {}

        # log5 = log.rolling(int(min(300/dt,len(log))))
        # log60 = log.rolling(int(min(300/dt,len(log))))
        if 'HDG' in log.columns:
                [maneuvers_indexes, tacking_deltaTWA, tacking_deltaCOG, tacking_deltaHDG, tacking_indexes, gybing_deltaTWA, \
                        gybing_deltaCOG, gybing_deltaHDG, gybing_indexes]= manoeuvres_gpx_easy_API(dt, log.Date_Time, log.TWA,
                        log.SOG_Kts, log.COG, tack_wand, gybe_wand, speed_treshold_perc_tack, speed_treshold_perc_gybe, HDG=log.HDG)
                deltatackHDG = np.mean(tacking_deltaHDG)
                deltagybeHDG = np.mean(gybing_deltaHDG)

        else:
                [maneuvers_indexes, tacking_deltaTWA, tacking_deltaCOG, tacking_deltaHDG, tacking_indexes, gybing_deltaTWA, \
                        gybing_deltaCOG, gybing_deltaHDG, gybing_indexes]= manoeuvres_gpx_easy_API(dt, log.Date_Time, log.TWA,
                        log.SOG_Kts, log.COG, tack_wand, gybe_wand, speed_treshold_perc_tack, speed_treshold_perc_gybe)
                deltatackHDG = 'No info in database about heading'
                deltagybeHDG = 'No info in database about heading'

        deltatackTWA= np.mean(tacking_deltaTWA)
        deltagybeTWA = np.mean(gybing_deltaTWA)
        deltatackCOG= np.mean(tacking_deltaCOG)
        deltagybeCOG = np.mean(gybing_deltaCOG)

        # HERE WOULD COME THE FILTERS

        #Values up, down, reach
        sogmax = []
        sogmax5 = []
        sogmax60 = []
        sogmean= []
        time= []
        distance= []
        twamean= []
        compass_accuracy= [] # , port, starboard

        logup = log[abs(log.TWA) < upwind_angle]
        logdn = log[abs(log.TWA) > downwind_angle]
        logrch = log[(abs(log.TWA) < downwind_angle) & (abs(log.TWA) > upwind_angle)]

        for ilog in [log, log5min, log60min]:
                logup.append(ilog[abs(ilog.TWA) < upwind_angle])
                logdn.append(ilog[abs(ilog.TWA) > downwind_angle])
                logrch.append(ilog[(abs(ilog.TWA) < downwind_angle) & (abs(ilog.TWA) > upwind_angle)])

        for mlog in [logup, logdn, logrch]:
                sogmean.append(np.mean(mlog.SOG_Kts))
                time.append(len(mlog)*dt)
                distance.append(sum(mlog.Dist))
                twamean.append(angles_stats([abs(i) for i in mlog.TWA], 'Mean', twa=True))
                if 'DeltaCOG' in log.columns:
                        compass_accuracy.append(np.mean(mlog.DeltaCOG))

        logsup = []
        logsdn = []
        logsrch = []

        for ilog in [log, log5min, log60min]:
                logsup.append(ilog[abs(ilog.TWA) < upwind_angle])
                logsdn.append(ilog[abs(ilog.TWA) > downwind_angle])
                logsrch.append(ilog[(abs(ilog.TWA) < downwind_angle) & (abs(ilog.TWA) > upwind_angle)])

        for mlog in [logsup, logsdn, logsrch]:
                sogmax.append(max(mlog[0].SOG_Kts, default='No values in this category'))
                sogmax5.append(max(mlog[1].SOG_Kts, default='No values in this category'))
                sogmax60.append(max(mlog[2].SOG_Kts, default='No values in this category'))


        if 'DeltaCOG' in log.columns:
                compass_accuracy.append(np.mean(log[log.TWA<0].DeltaCOG))
                compass_accuracy.append(np.mean(log[log.TWA>0].DeltaCOG))
                compassdict = {"Upwind": compass_accuracy[0], "Downwind": compass_accuracy[1], "Reaching": compass_accuracy[2]
                        , "Port": compass_accuracy[3], "Starboard": compass_accuracy[4]}
        else:
                compassdict = 'Unavailable: no Heading information in database'

        speedovec=[0]+speedovec
        if 'DeltaSOG' in log.columns:
                speedodict = {}
                for i in range(len(speedovec)):
                        if i!=len(speedovec)-1:
                                speedodict[str(speedovec[i])+" to "+str(speedovec[i+1])+" kts"] = np.mean(log.DeltaSOG[(log.SOG_Kts>
                                        speedovec[i]) & (log.SOG_Kts<speedovec[i+1])])
                        else:
                                speedodict[str(speedovec[i])+" kts to Inf"] = np.mean(log.DeltaSOG[(log.SOG_Kts > speedovec[i])])
        else:
                speedodict = 'Unavailable: no BSP information in database'

        # return {"Mean_SOG":{"a":1, "b":2}, "Max_SOG_1s":sogmax, "Max_SOG_5min":sogmax5, "Max_SOG_1h":sogmax60, "Times":time,
        #         "Distances":distance, "Mean_TWA":twamean, "TWD_Max_Left":twd_left, "TWD_Max_Right":twd_right,
        #         "Tack_Delta_TWA_Avg":deltatack, "Gybe_Delta_TWA_Avg":deltagybe, "Compass_Accuracy":compass_accuracy, "Speedometer_Accuracy":speedo_accuracy,
        #         "Warnings":warnings}

        return {"SOG":{"Average":{"Upwind":sogmean[0],"Downwind":sogmean[1],"Reaching":sogmean[2]},
                        "Max":{"Upwind":sogmax[0],"Downwind":sogmax[1],"Reaching":sogmax[2]},
                        "Max_5min":{"Upwind":sogmax5[0],"Downwind":sogmax5[1],"Reaching":sogmax5[2]},
                        "Max_1h":{"Upwind":sogmax60[0],"Downwind":sogmax60[1],"Reaching":sogmax60[2]}},
                "Duration_h":{"Upwind":time[0]/3600,"Downwind":time[1]/3600,"Reaching":time[2]/3600},
                "Distances_m":{"Upwind":distance[0],"Downwind":distance[1],"Reaching":distance[2]},
                "TWA":{"Average":{"Upwind":twamean[0],"Downwind":twamean[1],"Reaching":twamean[2]}},
                "TWD":{"Max_Left":{'1s':twd_left[0],'5min':twd_left[1],'1h':twd_left[2]},
                       "Max_Right":{'1s':twd_right[0],'5min':twd_right[1],'1h':twd_right[2]},
                       "Average":twdmean},
                "TWS":{"Max":{"1s":twsmax[0],"5min":twsmax[1],"1h":twsmax[2]},
                       "Min": {"1s": twsmin[0], "5min": twsmin[1], "1h": twsmin[2]},
                        "Average":twsmean},
                "Maneuvers":{"Tack":{"Delta_TWA_Avg":deltatackTWA,"Delta_COG_Avg":deltatackCOG,"Delta_HDG_Avg":deltatackHDG},
                             "Gybe":{"Delta_TWA_Avg":deltagybeTWA,"Delta_COG_Avg":deltagybeCOG,"Delta_HDG_Avg":deltagybeHDG}},
                "Compass_Accuracy":compassdict, "Speedometer_Accuracy":speedodict,
                "Warnings":warnings}


# a=WarpRetrieve('cdc3', 'gascogne4552019', None, {"ass":2,"boo":'justin'}, 10, 10, None, None, None, None, None, None)
# a=WarpRetrieve('cdc3', 'entrainement_jan2020_d2_gps_only', None, None, None, None, None, None, None, None, None, None)

# a=WarpRetrieve('cdc3', 'gascogne4552019', {"start_time":"2019-05-16 13:00:00", "stop_time":"2019-05-16 16:00:00",
# 		"only_while_sailing":"True"}, None)

# entrainement_jan2020_d2_gps_only entrainement_oct2020_d3_with_gaps gascogne4552019 gascogne4552019_10k entrainement_oct2020_d3_no_gap


# import matplotlib.pyplot as plt
# fig, axs = plt.subplots(1, 1, sharex=True, sharey=True)
# plt.plot(log.Longitude[100:-100],log.Latitude[100:-100])
# plt.plot(log.Longitude[maneuvers_indexes],log.Latitude[maneuvers_indexes],'ko')
# plt.plot(log.Longitude[gybing_indexes],log.Latitude[gybing_indexes],'yo', ms=3)
# plt.plot(log.Longitude[tacking_indexes],log.Latitude[tacking_indexes],'ro', ms=3)
# axs.set_aspect=(1)
# axs.axis('off')
# plt.show()
