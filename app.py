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

	fires = pd.read_pickle('data/fires.pkl')
	fires.columns = ['fires', 'date', 'block']

	return properties, vi, defor, water, evapo, fires


properties, vi, defor, water, evapo, fires = load_data()


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


st.markdown("""

	------

	The %s hunting block, outfitted by _%s_, is %s square kilometers. The total
	fees associated with this concession are $%s, amounting to $%s per square
	kilometer. There are %s present in this concession.

	------

""" % (
		block_name, 
		outfitter,
		"{:,d}".format(area), 
		"{:,d}".format(fees), 
		"{:,d}".format(int(fees/area)),
		animal_string(animals)
	)
)

st.markdown("""

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
			hole=.5)
		]
	)

fig.update_traces(hoverinfo='label+value')

st.plotly_chart(fig, use_container_width=True)

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

	There is clearly a seasonal pattern of fires.  How does this year (in red)
	compare against previous years?  In other words, is the pattern of fires seen
	this year an anomaly?  The x-axis is _day of year_.  If the red line strays
	from the grey area, which represents the 95 percent confidence interval based
	on the previous 11 years, then that day's fire count is considered anomalous.

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

	3. Human modifcation (histogram for 2019)

	4. Land cover

	5. **Higher spatial and temporal resolution**.  Some measures are daily, through yesterday.  Some are annual.  For those,
	more up-to-date measures can be derived, but that would require a lot more
	work.

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

