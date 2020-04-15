import requests
import snippets.Warp10Util
import json
import pandas as pd
import numpy as np
from rest_framework import exceptions

def WarpRetrieve(url, token):

        variables = ["COG", "SOG", "HDG", "STW", "TWD", "TWS", "TWA", "AWS", "AWA", "STW_EFF"]

        print(url + ' / ' + token)

        script= r"'"+token+"'"   + "\n" \
                r"'Rt' STORE" + "\n" \
                r"$Rt AUTHENTICATE 1000000 LIMIT 10000 MAXOPS 10000 MAXLOOP"  + "\n" \
                r"'2019-05-17T14:00:00.000Z' 'start' STORE"  + "\n" \
                r"'2019-05-17T14:00:10.0Z' 'stop' STORE"  + "\n" \
                r"[ $Rt 'BoatData' { 'boat_id' 'cdc3' 'event_id' 'gascogne4552019' } $start $stop ] FETCH  0 GET 'BoatData' STORE"  + "\n" \
                r"$BoatData"  + "\n" \
                r"MVINDEXSPLIT { 'DOUBLE' '~.*{}' } ->GTS"  + "\n" \
                r"'input' STORE"  + "\n" \
                r"$input 0 GET 'cog' STORE"  + "\n" \
                r"$input 1 GET VALUES 'sog' STORE"  + "\n" \
                r"$input 2 GET VALUES 'hdg' STORE"  + "\n" \
                r"$input 3 GET VALUES 'stw' STORE"  + "\n" \
                r"$input 4 GET VALUES 'twd' STORE" + "\n" \
                r"$input 5 GET VALUES 'tws' STORE"  + "\n" \
                r"$input 6 GET VALUES 'twa' STORE"  + "\n" \
                r"$input 7 GET VALUES 'aws' STORE"  + "\n" \
                r"$input 8 GET VALUES 'awa' STORE"  + "\n" \
                r"$input 9 GET VALUES 'stw_eff' STORE"  + "\n" \
                r"$cog TICKS 'ticks' STORE"  + "\n" \
                r"$cog LOCATIONS 2 ->LIST 'locations' STORE"  + "\n" \
                r"$cog VALUES 'cog' STORE "  + "\n" \
                r"$locations 0 GET 'latitudes' STORE"  + "\n" \
                r"$locations 1 GET 'longitudes' STORE"  + "\n" \
                r"[ $ticks $latitudes $longitudes $cog $sog $hdg $stw $tws $twa $aws $awa $stw_eff ]"

        header = {"content-type": "application/text"}
        url += "/exec"
        print("Exec script from warp10... " + url)
        r = requests.post(url, headers=header,data=script)
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
        for i in range(3,3+len(variables)-1):
                var = variables[i - 3]
                df[var]=res[i]  # may contain some nan! can be tested with np.isnan()

        meanSOG=np.mean(df.SOG)

        return meanSOG
