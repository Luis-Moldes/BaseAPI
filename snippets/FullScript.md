'3Wus11ES3maQ6F5QZIx0Pg.CN8pPMJtlQqN.FzaIPtPLuqb1hV0Gva8QwLQDaf_aLJmqRcYNl7slSjSwBotH.AEMNlDWKHdXKEZITX6IGciPzNjINwjRWtVEb.NejybBEoiFQS3iCb.N7N6faUv60qpXm8Yp4YuCLHWeaNAeW7GG8TOjDJq7G.'
'Rt' STORE
$Rt AUTHENTICATE 1000000 LIMIT 10000 MAXOPS 10000 MAXLOOP
'0000-05-16T17:00:00.000Z' 'start' STORE
'2100-05-17T14:00:10.000Z' 'stop' STORE
[ $Rt 'BoatData' { 'boat_id' 'cdc3' 'event_id' 'entrainement_oct2020_d3_with_gaps' } $start $stop ] FETCH 0 GET 'BoatData' STORE
$BoatData
MVINDEXSPLIT { 'DOUBLE' '~.*{}' } ->GTS
'input' STORE
$input 0 GET 'cog' STORE
$input 1 GET VALUES 'sog' STORE
$input 2 GET VALUES 'hdg' STORE
$input 3 GET VALUES 'stw' STORE
$input 4 GET VALUES 'twd' STORE
$input 5 GET VALUES 'tws' STORE
$input 6 GET VALUES 'twa' STORE
$input 7 GET VALUES 'aws' STORE
$input 8 GET VALUES 'awa' STORE
$input 9 GET VALUES 'stw_eff' STORE
$cog TICKS 'ticks' STORE
$cog LOCATIONS 2 ->LIST 'locations' STORE
$cog VALUES 'cog' STORE
$locations 0 GET 'latitudes' STORE
$locations 1 GET 'longitudes' STORE
[ $ticks $latitudes $longitudes $cog $sog $hdg $stw $tws $twa $aws $awa $stw_eff ]

'3Wus11ES3maQ6F5QZIx0Pg.CN8pPMJtlQqN.FzaIPtPLuqb1hV0Gva8QwLQDaf_aLJmqRcYNl7slSjSwBotH.AEMNlDWKHdXKEZITX6IGciPzNjINwjRWtVEb.NejybBEoiFQS3iCb.N7N6faUv60qpXm8Yp4YuCLHWeaNAeW7GG8TOjDJq7G.'
'Rt' STORE
$Rt AUTHENTICATE 1000000 LIMIT 10000 MAXOPS 10000 MAXLOOP
'0000-05-16T17:00:00.000Z' 'start' STORE
'2100-05-17T14:00:10.000Z' 'stop' STORE
[ $Rt 'boat.data' { 'boat_id' 'cdc3' 'event_id' 'gascogne4552019' } $start $stop ] FETCH 0 GET 'BoatData' STORE
$BoatData
MVINDEXSPLIT { 'DOUBLE' '~.*{}' } ->GTS
'input' STORE

<%
  // Each time this macro is called, 5 elements are stacked up.
  // only the third one is useful for what we want to do
  // which contains the missing tick of the reference GTS in the GTS to complete,
  // in the form of a list [ tick lat lon elev value ]
  2 DROPN // retrieving the 3rd element 
  4 REMOVE // deleting the reference value from the list
  DROP // we don't do anything with this value
  [ NaN ] APPEND // the value is replaced by NaN
  3 ROLLD // get rid of the 4th and 5th elements 
  2 DROPN // initially in the stack (now 2nd and 3rd)
  // the top of the stack now contains [ tick lat lon elev NaN ]
  // if there were any data stacked upstream they are still there 
%> 'NANFILLER' STORE
$input 1 GET 'sog_nogap' STORE

$input 0 GET 'cog' STORE
$input 1 GET VALUES 'sog' STORE
$input 2 GET VALUES 'hdg' STORE
$input 3 GET VALUES 'stw' STORE
$input 4 GET VALUES 'twd' STORE
$input 5 GET VALUES 'tws' STORE

<% $input 6 GET $sog_nogap $NANFILLER 0 0 MACROFILLER FILL DROP SORT 'twa' STORE %>
<% [] 'awa' STORE %>
<% %>
TRY
<% 
$input 7 GET VALUES 'awa' STORE 
'sog_nogap' $NANFILLER 0 0 MACROFILLER FILL DROP SORT 'awa_nogap' STORE
%>
<% [] 'awa' STORE %>
<% %>
TRY
$cog TICKS 'ticks' STORE
$cog LOCATIONS 2 ->LIST 'locations' STORE
$cog VALUES 'cog' STORE
$locations 0 GET 'latitudes' STORE
$locations 1 GET 'longitudes' STORE
[ $ticks SIZE $latitudes SIZE $longitudes SIZE $cog SIZE $sog SIZE $hdg SIZE $stw SIZE $tws SIZE $twa SIZE $awa SIZE ] 