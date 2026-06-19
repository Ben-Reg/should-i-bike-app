# should-i-bike
A tool to help you decide whether you should drive or ride your bike. (Currently US only)

Command-line (python) and PWA available. Use the PWA here:
[https://ben-reg.github.io/should-i-bike-app/](https://ben-reg.github.io/should-i-bike-app/)
(No account necessary for the PWA - all data is saved directly on your device.)

## Who it is for
This tool is designed for people who commute by bike, riding the same route at the same times each day, who want a quick way to check what the weather will be like during their rides and a little help deciding if the weather warrents taking a car instead of biking.

## How it works
Uses your zip code to return weather data for your location from NOAA. You can set up rules that will be evaluated when the app checks the weather for your next ride.  Each rule has a numerical weight that you assign, and if the combined weight of all triggered rules is more than 10, it tells you to drive instead.
(For example, you can have a rule that will trigger when the temperature is above 95 degrees, or a slightly more complex rule where the Wind Direction contains 'S' and the wind speed is greater than 30 mph.)
