import requests
import snippets.Warp10Util
import json
import pandas as pd
import numpy as np
from rest_framework import exceptions
import snippets.Warp_Config as conf
from snippets.Tools import angles_stats

def WarpRetrieve(boat_id, event_id):

        url=conf.warp_url

        variables = conf.vars

        script= r"'"+conf.warp_token+"'"   + "\n" \
                r"'Rt' STORE" + "\n" \
                r"$Rt AUTHENTICATE 1000000 LIMIT 1000000 MAXOPS 10000 MAXLOOP"  + "\n" \
                r"'2000-05-16T15:00:00.000Z' 'start' STORE"  + "\n" \
                r"'2030-05-16T17:00:10.0Z' 'stop' STORE"  + "\n" \
                r"[ $Rt '" + conf.name + "' { 'boat_id' '"+boat_id+"' 'event_id' '"+event_id+"' } $start $stop ] FETCH  0 GET 'BoatData' STORE"  + "\n" \
                r"$BoatData"  + "\n" \
                r"MVINDEXSPLIT { 'DOUBLE' '~.*{}' } ->GTS"  + "\n" \
                r"'input' STORE"  + "\n" \
                r"<% 2 DROPN 4 REMOVE DROP [ NaN ] APPEND 3 ROLLD 2 DROPN %> 'NANFILLER' STORE" + "\n" \
                r"$input 1 GET 'sog_nogap' STORE" + "\n" \
                r"$input 0 GET 'cog' STORE"  + "\n" \
                r"$input 1 GET VALUES 'sog' STORE" + "\n" \
                r"<% $input 2 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'hdg' STORE %>" + "\n" \
                r"<% [] 'hdg' STORE %>" + "\n" \
                r"<% %>" + "\n" \
                r"TRY" + "\n" \
                r"<% $input 3 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT VALUES 'stw' STORE %>" + "\n" \
                r"<% [] 'stw' STORE %>" + "\n" \
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
                r"[ $ticks $latitudes $longitudes $cog $sog $hdg $stw $twd $tws $twa $aws $awa $stw_eff ]"


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
        df = pd.DataFrame({'timestamp':res[0],
                            'lat':res[1],
                            'lon':res[2]})
        df['timestamp']= df['timestamp'].map(lambda ts: snippets.Warp10Util.EpochToTime(int(ts)))
        for i in range(len(variables)):
                var = variables[i]
                if len(res[i+3])!=0:
                        df[var]=res[i+3]  # may contain some nan! can be tested with np.isnan()

        return np.mean(df.SOG), angles_stats(df.COG, 'Mean')

[a,b]=WarpRetrieve('cdc3', 'entrainement_oct2020_d3_no_gap')
# entrainement_jan2020_d2_gps_only entrainement_oct2020_d3_with_gaps gascogne4552019 gascogne4552019_10k entrainement_oct2020_d3_no_gap
