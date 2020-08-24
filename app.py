import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import datetime
from statsmodels.tsa.stattools import adfuller
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px


st.header("Prioritizing concessions based on Earth observation")


st.markdown("""

> _Conservation is not big business. Resources are scarce. Consistent and
credible data are required for to solve the poblem of constrained
optimization.  If you had USD$1M, which concessions would you conserve?_

""")

@st.cache(persist=True)
def load_data(plot=True):

	properties = pd.read_pickle('data/properties.pkl')
	vi = pd.read_pickle('data/vi.pkl')
	defor = pd.read_pickle('data/defor.pkl')
	water = pd.read_pickle('data/waterclass.pkl')
	evapo = pd.read_pickle('data/evapotranspiration.pkl')
	pop = pd.read_pickle('data/population.pkl')
	soil = pd.read_pickle('data/soil.pkl')
	carbon = pd.read_pickle('data/carbon.pkl')
	forestcarbon = pd.read_pickle('data/forestcarbon.pkl')
	weather = pd.read_pickle('data/weather.pkl')

	fires = pd.read_pickle('data/fires.pkl')
	fires.columns = ['fires', 'date', 'block']

	return properties, vi, defor, water, evapo, fires, pop, soil, carbon, forestcarbon, weather


properties, vi, defor, water, evapo, fires, pop, soil, carbon, forestcarbon, weather = load_data()


st.markdown("""

	This roughcut web application is intended to illustrate both the baseline and
	real-time environmental measurements on possible concessions.  Possible
	metrics include vegetatiwon indices, carbon content, deforestation, among
	others.  The front-end is simple.  A fancy user interface or graphics can be
	built.  The objective of this early application is to settle on the
	measurements that are most useful for reporting and concession
	prioritization.

""")

block_names = list(properties["HUNT_BLOCK"])

block_name = st.selectbox(
	'Select the Hunting Block',
	block_names
)

area = int(properties.loc[properties["HUNT_BLOCK"] == block_name, "AREA"])
fees = int(properties.loc[properties["HUNT_BLOCK"] == block_name, "TOTALFEES"])
outfitter = list(properties.loc[properties["HUNT_BLOCK"] == block_name, "OUTFITTER2"])[0]

animal_names = ["BUFFALO", "IMPALA", "LEOPARD", "LION", "PUKU"]
animals = properties.loc[properties["HUNT_BLOCK"] == block_name, animal_names].to_dict()


def animal_string(animals):

	def _filter_animals(a):
		name, countdict = a
		x = list(countdict.values())
		if x[0] > 0:
			return name.capitalize()

	l = [_filter_animals(x) for x in animals.items()]
	full_l = [i for i in l if i]
	if len(full_l) == 0:
		return "no documented animals"
	elif len(full_l) == 1:
		return "only documented %ss"
	else:
		return "multiple (%s) documented animals" % ", ".join(full_l)


popest = int(pop.loc[pop['block'] == block_name, 'population2018'])

st.markdown("""

	------

	The %s hunting block, outfitted by _%s_, is **%s** square kilometers. The total
	fees associated with this concession are **$%s**, amounting to **$%s** per square
	kilometer. There are %s present in this concession.

	According to the [Facebook population density
	maps](https://dataforgood.fb.com/tools/population-density-maps/), using
	building counts derived from high-resolution satellite imagery, there are
	**%s** people residing (at least temporarily) within the boundaries of the
	concession.

""" % (
		block_name, 
		outfitter,
		"{:,d}".format(area), 
		"{:,d}".format(fees), 
		"{:,d}".format(int(fees/area)),
		animal_string(animals),
		"{:,d}".format(popest)
	)
)

carbon_df = carbon[carbon["block"] == block_name]

carbon_df["tC"] = carbon_df["carbon"] * 9 * carbon_df["frequency"]

mtC = np.round(sum(carbon_df["tC"])/1000000, 2)

avgtC_per_hectare = sum(carbon_df["tC"])/sum(carbon_df["frequency"])

st.markdown("""

	----

	## Carbon

	Carbon storage is one of the few ecosystem services with a market value. This
	section reports the above- and below-ground carbon, as estimated from global
	models that rely on remotely sensed sources of information.  These are very
	rough estimates.  A more precise estimate at higher resolution would be
	required to facilitate carbon market transactions.  

	The total carbon within the **%s** concession, both above- and below-ground,
	is estimated to be **%s** million tonnes of Carbon (an average of **%s**
	tC/ha).  The aggregate carbon data are described in the article [_Mapping
	co-benefits for carbon storage and biodiversity to inform conservation policy
	and action_](https://royalsocietypublishing.org/doi/10.1098/rstb.2019.0128).

""" % (
		block_name,
		mtC,
		np.round(avgtC_per_hectare/9, 2)
	)
)


c = alt.Chart(carbon_df).mark_bar(
		color="#A9BEBE",
		size=2.5
	).encode(
	    x=alt.X(
	    	'carbon:Q',
        	scale=alt.Scale(domain=[0,150]),
        	title="Tonnes (t) of Carbon per hectare (ha)"
        ),
	    y=alt.Y(
	    	'frequency:Q',
	    	title="Number of pixels (300m)",
	    	scale=alt.Scale(domain=[0,1600], clamp=True)
	    )
)

st.altair_chart(c, use_container_width=True)


soil_df = soil[soil["block"] == block_name]

st.markdown(""" 

	### Soil organic carbon density

	[Open Land Map](https://www.openlandmap.org/) publishes information on soil
	carbon at six different depths.  The methodology is described
	[here](https://github.com/Envirometrix/LandGISmaps#soil-properties-and-classes).
	This data is summarized below for the **%s** concession.

""" % block_name)


c = alt.Chart(soil_df).mark_area(interpolate="basis").encode(
    alt.X(
    	'carbon_g_per_kg',
    	title="Carbon density (g/kg)",
    	scale=alt.Scale(domain=[0,6.5], clamp=True)
    ),
    alt.Y(
    	'frequency:Q',
    	title="",
    ),
    color=alt.Color(
    	"depth:N", 
    	legend=None, 
    	scale=alt.Scale(scheme='brownbluegreen',reverse=True),
    	sort=['0cm', '10cm', '30cm', '60cm', '100cm', '200cm']
    ),
    row=alt.Row(
    	'depth:N',
    	title="Soil depths // pixel frequency",
    	sort=['0cm', '10cm', '30cm', '60cm', '100cm', '200cm'],
    	spacing=0
    )
).properties(
    title='Frequency (number of 250m pixels) of carbon densities at six different soil depths',
    height=60
).configure_axis(
	grid=False, domain=False
).configure_view(strokeWidth=0)


st.altair_chart(c, use_container_width=True)


forestcarbon_df = forestcarbon[
	(forestcarbon["block"] == block_name) & \
	(forestcarbon["carbon"] > 0)
]

forestcarbon_df["tC"] = forestcarbon_df["carbon"] * 9 * forestcarbon_df["frequency"]

forest_mtC = np.round(sum(forestcarbon_df["tC"])/1000000, 2)

forest_carbon_percent = np.round(100*forest_mtC/mtC, 2)

st.markdown("""

	### Forest carbon

	The Oak Ridge National Lab, in partnership with NASA, have [published a
	harmonized and consistent global map of aboveground
	biomass](https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1763). The data are
	published at 300-meter spatial resolution for 2010, reporting tonnes Carbon
	per hectare.

	The forest/non-forest map is calculated from [ALOS PALSAR data
	(2007–2010)](). The map is generated by classifying the SAR image
	(backscattering coefficient) in the global 25m resolution PALSAR-2/PALSAR SAR
	mosaic. Here, forest is defined as natural forest with area larger than 0.5
	ha and forest cover over 10 percent. This definition is the same as the Food
	and Agriculture Organization (FAO) definition.

	The total forest carbon within the **%s** concession is **%s** million tonnes
	of Carbon, which is **%s** percent of the total, aggregate (above- and
	below-ground) Carbon.

""" % (
		block_name,
		forest_mtC,
		forest_carbon_percent
	)
)


c = alt.Chart(forestcarbon_df).mark_bar(
		color="#A9BEBE",
		size=2.5
	).encode(
	    x=alt.X(
	    	'carbon:Q',
        	scale=alt.Scale(domain=[0,150]),
        	title="Tonnes (t) of Carbon per hectare (ha)"
        ),
	    y=alt.Y(
	    	'frequency:Q',
	    	title="Number of pixels (300m)",
	    	scale=alt.Scale(domain=[0,1600], clamp=True)
	    )
)

st.altair_chart(c, use_container_width=True)


st.markdown("""

	----

	## Fires

	The [Fire Information for Resource Management
	System](https://earthdata.nasa.gov/earth-observation-data/near-real-time/firms)
	(FIRMS) was developed to provide near real-time active fire locations to
	natural resource managers that faced challenges obtaining timely
	satellite-derived fire information.  We report the fires for each day since
	January 1, 2001 above an intensity threshold of 300 Kelvin.  

""")

fires_df = fires[fires["block"]==block_name]

c = alt.Chart(fires_df).mark_bar(
		color="#e45756",
		size=0.6
	).encode(
	    x='date:T',
	    y='fires'
)

st.altair_chart(c, use_container_width=True)

st.markdown("""

	### Fire anomalies

	There is clearly a seasonal pattern of fires.  How does this year (in red)
	compare against previous years?  In other words, is the pattern of fires seen
	this year an anomaly?  The x-axis is _day of year_.  If the red line strays
	from the grey area, which represents the 95 percent confidence interval based
	on the previous 11 years, then that day's fire count is considered anomalous.
	 The bottomline for the initial set of concessions is that the fire count is
	down this year, relative to the previous decade.

""")

fires_df['year'] = pd.DatetimeIndex(fires_df['date']).year
fires_df['day_of_year'] = pd.DatetimeIndex(fires_df['date']).dayofyear
fires_df_early = fires_df[fires_df["year"] < 2020]
fires_df_late = fires_df[fires_df["year"] == 2020]

fires_ci = alt.Chart(fires_df_early).mark_errorband(extent='ci').encode(
	    x='day_of_year',
	    y='fires'
)


fires_smooth = alt.Chart(fires_df_late).mark_line(
	color='#e45756'
).transform_window(
	rolling_mean='mean(fires)',
	frame=[-10, 10]
).encode(
	x=alt.X(
		'day_of_year',
		axis=alt.Axis(
			title=""
		),
	),
	y=alt.Y(
		'rolling_mean:Q'
	)
)

st.altair_chart(fires_ci + fires_smooth, use_container_width=True)




defor_df = defor[defor["block"]==block_name]
total_defor = sum(defor["hectares"]) 
total_defor_perc = int(10000 * total_defor/(area * 100))
total_defor_perc = total_defor_perc/100

st.markdown("""

	----

	## Deforestation 

	Annual tree cover loss between 2000-2019,  detected from NASA satellite
	imagery at 30-meter resolution.  Defined as a stand-replacement disturbance
	(achange from a forest to non-forest state).  For **%s**, these numbers
	suggest that  **%s percent** of the concession was impacted by tree cover
	loss.

""" %(block_name, total_defor_perc) )

c = alt.Chart(defor_df).mark_bar(
		color="#e45756"
	).encode(
	    x='year:O',
	    y='hectares'
)

st.altair_chart(c, use_container_width=True)

water_df = water[water["block"]==block_name]
total_water_area = np.round(sum(water_df["area_km2"]), 2)
percent_water_area = np.round(100*total_water_area/area, 2)

st.markdown("""

	----

	## Surface water 

	The Joint Research Centre reports on the location and temporal distribution
	of surface water from 1984 to 2019 and provides statistics on the extent and
	change of those water surfaces.  The data are derived from Sentinel satellite
	imagery, and the methods are published in
	[_Nature_](https://www.nature.com/articles/nature20584).  The following chart
	summarizes a 35-year analysis of the JRC output data, representing a
	comprehensive analysis of surface water and how it has changed over time for
	the **%s** concession.  Of the %s square kilometers in the concession, **%s**
	(%s percent) have been, at some point, characterized by surface water or
	surface water change.  The following chart illustrates the composition of the
	surface water classes and surface water transitions in the concession. 
	Hovering over the chart will display the area in square kilometers of each
	water class/transition.

""" %(
		block_name, 
		"{:,d}".format(area), 
		total_water_area, 
		percent_water_area
	)
)

labels = water_df["water_label"]
values = water_df["area_km2"]

# Use `hole` to create a donut-like pie chart
fig = go.Figure(
	data=[
		go.Pie(
				labels=labels, 
				values=values, 
				hole=.5,
				marker=dict(
					colors=[
						"rgb(165,0,38)",
						"rgb(215,48,39)",
						"rgb(244,109,67)",
						"rgb(253,174,97)",
						"rgb(254,224,144)",
						"rgb(224,243,248)",
						"rgb(171,217,233)",
						"rgb(116,173,209)",
						"rgb(69,117,180)",
						"rgb(49,54,149)"
					]
				)
			)
		]
	)

fig.update_traces(hoverinfo='label+value')
fig.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.1,
    xanchor="right",
    x=1
))

st.plotly_chart(fig, use_container_width=True)


st.markdown("""

	-------

	## Vegetation 

	Vegetation indices may be a leading indicator for ecosystem health. 
	Unhealthy or sparse vegetation reflects more visible light and less
	near-infrared light. This is the basic premise for the [two predominant
	vegetation
	indices](https://earthobservatory.nasa.gov/features/MeasuringVegetation/measuring_vegetation_2.php),
	the Normalized Difference Vegetation Index and the Enhanced Vegetation Index.

""")


vegetation_index_name = st.selectbox(
	'Vegetation Index',
	[
		"Normalized Difference Vegetation Index (NDVI)",
		"Enhanced Vegetation Index (EVI)"
	]
)

if vegetation_index_name == "Normalized Difference Vegetation Index (NDVI)":
	vi_name = "NDVI"
else:
	vi_name = "EVI"

vi_df = vi[vi["block"]==block_name]

nfdrs_data = alt.Chart(vi_df).mark_line(
	color="#A9BEBE", 
	size=1
).encode(
	x='date:T',
	y=vi_name
)

st.altair_chart(nfdrs_data, use_container_width=True)

evapo_df = evapo[evapo["block"]==block_name]
evapo_df.columns = ["evapotranspiration", "date", "block"]

st.markdown("""

	Evapotranspiration is the sum of evaporation from the land surface plus
transpiration from plants. Like the vegetation indices, it is a useful
indicator of landscape level change. The FAO data to monitor [Water
Productivity through Open access of Remotely sensed derived
data](http://www.fao.org/3/i8225en/I8225EN.pdf) (WaPOR) provides access to 12
years of continued observations over Africa.  The data are collected daily at
20km resolution.  It may be useful to monitor long-term trends.

""")

evapo_window = st.slider(
	'Symmetric moving average window (days on either side) to visualize long-term trends',
	10, 200, 50
)

evapo_raw = alt.Chart(evapo_df).mark_circle(
	color="#A9BEBE", 
	size=1
).encode(
	x='date:T',
	y='evapotranspiration'
)

evapo_smooth = alt.Chart(evapo_df).mark_line(
	color='#e45756'
).transform_window(
	rolling_mean='mean(evapotranspiration)',
	frame=[-evapo_window, evapo_window]
).encode(
	x=alt.X(
		'date:T',
		axis=alt.Axis(
			title=""
		),
	),
	y=alt.Y(
		'rolling_mean:Q', 
		axis=alt.Axis(
			title="Evapotranspiration (mm)"
		)
	)
)

st.altair_chart(evapo_raw + evapo_smooth, use_container_width=True)


st.markdown("""

	-------

	## Weather and climate

	The weather information, daily precipitation and daily temperature, are
	derived from the [Copernicus Climate Change Service ERA5 atmospheric
	reanalysis](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels?tab=overview).
	The spatial resolution is 0.25° by 0.25° gridded degree, which is equivalent
	to about 27.75 km at the Equator.

	The timeseries graph illustrates the daily confidence interval for 2000-2019,
	with the daily measurements from 2020 overlaid in red.
	

""")

weather_df = weather[weather["block"]==block_name]
weather_df['year'] = pd.DatetimeIndex(weather_df['date']).year
weather_df['day_of_year'] = pd.DatetimeIndex(weather_df['date']).dayofyear
weather_df_early = weather_df[weather_df["year"] < 2020]
weather_df_late = weather_df[weather_df["year"] == 2020]

weather_variable = st.selectbox(
	'Weather variable',
	['Daily mean temperature (C)', 'Daily precipitation (cm)']
)

var_dicts = {
	'Daily mean temperature (C)': {'varname': 'temp_celsius', 'units': 'Centimeters'}, 
	'Daily precipitation (cm)': {'varname': 'precip_cm', 'units': 'Celsius'}
}

weather_ci = alt.Chart(weather_df_early).mark_errorband(extent='ci').encode(
	    x='day_of_year',
	    y=alt.Y(
	    	var_dicts[weather_variable]['varname'], 
	    	scale=alt.Scale(zero=False),
	    	title=""
	    )
)


weather_smooth = alt.Chart(weather_df_late).mark_line(
	color='#e45756'
).transform_window(
	rolling_mean='mean(%s)' % var_dicts[weather_variable]['varname'],
	frame=[-2, 2]
).encode(
	x=alt.X(
		'day_of_year',
		axis=alt.Axis(
			title=""
		),
	),
	y=alt.Y(
		'rolling_mean:Q',
		title="%s" % var_dicts[weather_variable]['units'],
		scale=alt.Scale(zero=False)
	)
)

st.altair_chart(weather_ci + weather_smooth, use_container_width=True)



st.markdown("""

	----

	## Next steps
	There are a lot of other views and metrics that may be useful.

	1. **Optimization dashboard**.  Basically a way to construct and monitor a
	portfolio of concessions based on Earth observation data.  This sort of
	dashboard will also help to report on dimensions like _Permanence_ or
	_Additionality_ for selected concessions &mdash; interventions yield outcomes that
	are off-baseline.

	2. **Metrics for 'nearby' areas**. Comparison of protected area metrics
	against other areas.  The concept of 'nearby' can be based on geographic, or
	another measure of similarity. Statistical matching has been used in academic
	studies to demonstrate the [efficacy of multiple use protected
	areas](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0022722).

	3. **Higher spatial and temporal resolution**.  Some measures are daily,
	through yesterday.  Some are annual.  For those, more up-to-date measures can
	be derived, but that would require a lot more work.

	4. **Additional datasets**.  Including building outlines and other
	infrastructure, as well as land use.  weather anomalies and climate
	(mitigate, proactively, the impact of climate change.) 

""")

# window = st.slider(
# 	'Moving average window (years)',
# 	3, 20, 15
# )


# nfdrs = pd.read_pickle("data/nfdrs.pkl")



# nfdrs_data = alt.Chart(nfdrs).mark_circle(
# 	color="#A9BEBE", 
# 	size=1
# ).encode(
# 	x='date:T',
# 	y=nfdrs_var
# )

# nfdrs_smooth = alt.Chart(nfdrs).mark_line(
# 	color='#e45756'
# ).transform_window(
# 	rolling_mean='mean(%s)' % nfdrs_var,
# 	frame=[-nfdrs_window, nfdrs_window]
# ).encode(
# 	x=alt.X(
# 		'date:T',
# 		axis=alt.Axis(
# 			title=""
# 		),
# 	),
# 	y=alt.Y(
# 		'rolling_mean:Q', 
# 		scale=alt.Scale(domain=vis[nfdrs_var]),
# 		axis=alt.Axis(
# 			title="%s" % nfdrs_var
# 		)
# 	)
# )


# if nfdrs_option == 'True':
# 	st.altair_chart(nfdrs_data + nfdrs_smooth, use_container_width=True)
# else:
# 	st.altair_chart(nfdrs_smooth, use_container_width=True)

