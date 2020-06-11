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
from snippets.functions_API import calculate_TWA, datetoindex, manoeuvres_gpx_easy_API

def WarpRetrieve(boat_id, event_id, start_time, stop_time, twd, tws, upwind_angle, downwind_angle, tack_wand, gybe_wand,
                 speedo_calib, speed_treshold_perc):


        url=conf.warp_url

        variables = conf.vars

        warnings=[]

        if upwind_angle==None:
                upwind_angle=80
                warnings.append('- No upwind reaching wind angle found in input, it will be set to 80º')
        if downwind_angle==None:
                downwind_angle=110
                warnings.append('- No downwind reaching wind angle found in input, it will be set to 110º')

        if tack_wand==None:
                tack_wand=[20,40,15] #Time before, after, average
                warnings.append('- No parameters for tack analysis found in input, default values will be used')
        if gybe_wand==None:
                gybe_wand=[30,60,15] #Time before, after, average
                warnings.append('- No parameters for gybe analysis found in input, default values will be used')

        if speedo_calib == None:
                speedo_calib = [5,8]
                warnings.append('- No parameters for speedometer calibration steps found in input, default values will be used [5,8]')

        if speed_treshold_perc == None:
                speed_treshold_perc = 0.7
                warnings.append('- No parameters for maneuver selection found in input, it will be set to 85% of the mean SOG')

        if start_time==None or stop_time==None:
                need_times='T'
                start_str = '2015-05-16T15:00:00.000Z'
                stop_str = '2100-05-16T17:00:10.000Z'
                warnings.append('- No analysis times found in input')
        else:
                need_times='F'
                start_str = start_time[:10] + 'T' + start_time[-8:] + '.000Z'
                stop_str = stop_time[:10] + 'T' + stop_time[-8:] + '.000Z'

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
                r"0 'mode' STORE" + "\n" \
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
                r"$input 1 GET VALUES 'sog' STORE" + "\n" \
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
                r"<% $input 4 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'twd' STORE %>" + "\n" \
                r"<% [] 'twd' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 5 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'tws' STORE %>" + "\n" \
                r"<% [] 'tws' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 6 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'twa' STORE %>" + "\n" \
                r"<% [] 'twa' STORE %>" + "\n" \
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
                r"$locations 0 GET 'latitudes' STORE"  + "\n" \
                r"$locations 1 GET 'longitudes' STORE"  + "\n" \
                r"[ $ticks $latitudes $longitudes $cog $sog $hdg $stw $twd $tws $twa $aws $awa $stw_eff $DeltaCOG $DeltaSOG $mode ]" + "\n"


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
        res=res[0]
        # build dataframe
        log = pd.DataFrame({'timestamp':res[0],
                            'lat':res[1],
                            'lon':res[2]})
        log['timestamp']= log['timestamp'].map(lambda ts: snippets.Warp10Util.EpochToTime(int(ts)))
        for i in range(len(variables)):
                var = variables[i]
                if len(res[i+3])!=0:
                        log[var]=res[i+3]  # may contain some nan! can be tested with np.isnan()


################################################################################################################################

        log=log.rename(columns={"timestamp": "Date_Time", "lat": "Latitude", "lon": "Longitude", "SOG": "SOG_Kts"})
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
        else:
                warnings.append('- Sailing modes info was found in database!')

        #TIME REDUCTION

        if 'TWD' not in log.columns:
                if twd is None:
                        log['TWD'] = RememberTime(log)
                        log['TWS'] = pd.Series(np.ones(len(log)) * 10)
                        warnings.append('- No info about wind found in database or input, it will be estimated')
                else:
                        log['TWD'] = pd.Series(np.ones(len(log)) * twd)
                        log['TWS'] = pd.Series(np.ones(len(log)) * tws)

                twd_left=log['TWD'][0]
                twd_right = log['TWD'][0]

        else:
                twd5min=log.TWD.rolling(int(min(300 / dt, len(log)))).mean()
                twd_left=np.nanmin(twd5min)
                twd_right = np.nanmax(twd5min)

        if 'TWA' not in log.columns:
                log['TWA'] = calculate_TWA(log.Date_Time, log.TWD, log.COG)
        else:
                log['TWA'] = [to180(i) for i in log['TWA']]

        if 'DeltaCOG' in log.columns:
                log['DeltaCOG'] = [abs(to180(i)) for i in log['DeltaCOG']]

        log['Dist'] = log['SOG_Kts'] * dt * 1852 / (3600)

        [maneuvers_indexes, tacking_deltaTWA, tacking_indexes, gybing_deltaTWA, gybing_indexes]=\
                manoeuvres_gpx_easy_API(dt, log.Date_Time, log.TWA, log.SOG_Kts, log.COG, tack_wand, gybe_wand, speed_treshold_perc)

        deltatack=np.mean(tacking_deltaTWA)
        deltagybe = np.mean(gybing_deltaTWA)

        # HERE WOULD COME THE FILTERS

        logup = log[abs(log.TWA) < upwind_angle]
        logdn = log[abs(log.TWA) > downwind_angle]
        logrch = log[(abs(log.TWA) < downwind_angle) & (abs(log.TWA) > upwind_angle)]

        #Values up, down, reach
        sogmax = []
        sogmax5 = []
        sogmax60 = []
        sogmean= []
        time= []
        distance= []
        twamean= []
        compass_accuracy= [] # , port, starboard

        for mlog in [logup, logdn, logrch]:
                sogmax.append(np.nanmax(mlog.SOG_Kts))
                sogmax5.append(np.nanmax(mlog.SOG_Kts.rolling(int(min(300/dt,len(mlog)))).mean()))
                sogmax60.append(np.nanmax(mlog.SOG_Kts.rolling(int(min(3600/dt,len(mlog)))).mean()))
                sogmean.append(np.mean(mlog.SOG_Kts))
                time.append(len(mlog)*dt)
                distance.append(sum(mlog.Dist))
                twamean.append(angles_stats([abs(i) for i in mlog.TWA], 'Mean', twa=True))
                if 'DeltaCOG' in log.columns:
                        compass_accuracy.append(np.mean(mlog.DeltaCOG))

        if 'DeltaCOG' in log.columns:
                compass_accuracy.append(np.mean(log[log.TWA<0].DeltaCOG))
                compass_accuracy.append(np.mean(log[log.TWA>0].DeltaCOG))
        else:
                compass_accuracy = 'Unavailable: no Heading information in database'

        if 'DeltaSOG' in log.columns:
                speedo_accuracy = [np.mean(log[log.SOG_Kts<speedo_calib[0]].DeltaSOG),np.mean(log[log.SOG_Kts>speedo_calib[0]
                        & log.SOG_Kts<speedo_calib[1]].DeltaSOG), np.mean(log[log.SOG_Kts>speedo_calib[1]].DeltaSOG)]
        else:
                speedo_accuracy = 'Unavailable: no BSP information in database'

        return {"Mean_SOG":sogmean, "Max_SOG_1s":sogmax, "Max_SOG_5min":sogmax5, "Max_SOG_1h":sogmax60, "Times":time,
                "Distances":distance, "Mean_TWA":twamean, "TWD_Max_Left":twd_left, "TWD_Max_Right":twd_right,
                "Tack_Delta_TWA_Avg":deltatack, "Gybe_Delta_TWA_Avg":deltagybe, "Compass_Accuracy":compass_accuracy, "Speedometer_Accuracy":speedo_accuracy,
                "Warnings":warnings}

# a=WarpRetrieve('cdc3', 'gascogne4552019', '2019-05-16 13:00:00', '2019-05-16 15:40:00', 10, 10, None, None, None, None)
# a=WarpRetrieve('cdc3', 'entrainement_jan2020_d2_gps_only', None, None, None, None, None, None, None, None, None, None)

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
