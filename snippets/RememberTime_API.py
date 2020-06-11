
import numpy as np
from snippets.Tools_API import angles_stats, lowpass
from snippets.functions_API import read_parameters, calculate_cog_NoFilter, Wind_Dir

def RememberTime(log):

    params = read_parameters('parameters_gpx_easywind.dat')
    dt = params['dt']

    # if config != 'CSV':
    #     [log.Latitude,log.Longitude] = coord_interpol(log.Latitude,log.Longitude,log.Date_Time) #Processes repeated values
    #     log = time_interpol(log, dt)
    # else:
    #     [log.Latitude,log.Longitude] = coord_interpol_reverse(log.Latitude,log.Longitude,log.Date_Time)

    #log = time_interpol(log, dt)

    lat = log.Latitude
    lon = log.Longitude


    log['SOG_Kts']=lowpass(log['SOG_Kts'],params['lowpass_freq'])
    sog_mean = np.mean(log['SOG_Kts'])

    # i = 0
    # j = 0
    # labelindexes = []
    # endindexes = []
    # starts_str=[]
    # stops_str=[]
    # st = 1
    # for spd in range(len(log['SOG_Kts'])):
    #
    #     if log['SOG_Kts'][spd] < 0.7 * sog_mean:
    #         i = i + 1
    #         j = 0
    #     else:
    #         j = j + 1
    #         if j > 7 / dt:
    #             if i > 3*params['SD_Time'] / dt:
    #                 labelindexes.append(spd)
    #                 starts_str.append(str(log.Date_Time[spd])[11:])
    #                 st = 0
    #             i = 0
    #
    #     if (i > 3*params['SD_Time'] / dt and st == 0):
    #         endindexes.append(spd)
    #         stops_str.append(str(log.Date_Time[spd])[11:])
    #         st = 1

    # if len(starts_str)>len(stops_str):
    #     stops_str.append(str(log.Date_Time[len(log.Date_Time)-1])[11:])
    #     endindexes.append(len(log.Date_Time)-1)

    cogs=[]
    sogs=[]
    manind=[]

    half_man=int(params['Man_Time']/2)
    wait=int(10/dt)

    spd=wait + params['Man_Time']
    while spd<(len(log['SOG_Kts']) - wait - params['Man_Time']):
        speed_before=np.mean(log['SOG_Kts'][(spd-half_man-wait):(spd-half_man)])
        speed_after=np.mean(log['SOG_Kts'][(spd+half_man):(spd+half_man+wait)])
        bearing_before=angles_stats(calculate_cog_NoFilter(lat[(spd-half_man-wait):(spd-half_man)].values, lon[(spd-half_man-wait):(spd-half_man)].values,
                                     log.Date_Time[(spd-half_man-wait):(spd-half_man)].values),'Mean')
        bearing_after=angles_stats(calculate_cog_NoFilter(lat[(spd+half_man):(spd+half_man+wait)].values, lon[(spd+half_man):(spd+half_man+wait)].values,
                                    log.Date_Time[(spd+half_man):(spd+half_man+wait)].values),'Mean')

        turn=abs(bearing_before-bearing_after)
        if turn>180:
            turn=360-turn

        if ((turn > 80) and (0.5*(speed_before+speed_after) > 0.7 * sog_mean)): #man detected!

            #Extend your range of analysis (before, with this much rang it would not detect mans properly)

            bearing_before2 = angles_stats(calculate_cog_NoFilter(lat[(spd - half_man - 3*wait):(spd - half_man - wait)].values,
                                                    lon[(spd - half_man - 3*wait):(spd - half_man - wait)].values,
                                                    log.Date_Time[(spd - half_man - 3*wait):(spd - half_man - wait)].values),'Mean')
            bearing_after2 = angles_stats(calculate_cog_NoFilter(lat[(spd + half_man+ wait):(spd + half_man + 3*wait)].values,
                                                   lon[(spd + half_man+ wait):(spd + half_man + 3*wait)].values,
                                                   log.Date_Time[(spd + half_man+ wait):(spd + half_man + 3*wait)].values),'Mean')

            direction=(bearing_before2+bearing_after2)*0.5

            turn = abs(bearing_before2 - bearing_after2)
            if turn > 180:
                turn = 360 - turn

            if turn>90:
                direction=direction+180
            if direction>360:
                direction=direction-360

            cogs.append(direction)
            sogs.append((speed_before+speed_after)*0.5)
            manind.append(spd)
            spd = spd + 30
        else:
            spd=spd+1

    mean_sogs=np.mean(sogs)

    medw=Wind_Dir(log, cogs, sogs, mean_sogs)

    return medw

if __name__ == "__main__":
  #  log, event, phases, log_mess = read_files(["Input\sergi_13-05-19.gpx","Input\easywind_13-05-19.csv"], 'GPX + EasyWind')
  #  print(log_mess)
    RememberTime(['Input/FRA 213932_Jean Baptiste BernazR6.csv'], r'Input\parameters_gpx_easywind.dat')
  # RememberTime(['Input/ARG 1_Lange&Carranza-a.csv'], r'Input\parameters_gpx_easywind.dat')
