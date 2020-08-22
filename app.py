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
	return properties, vi, defor, water


properties, vi, defor, water = load_data()


st.markdown("""

	This roughcut web application is intended to illustrate both the baseline and
	real-time environmental measurements on possible concessions.  Possible
	metrics include vegetation indices, carbon content, deforestation, among
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
print(outfitter)

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
	Vegetation indices may be a leading indicator for ecosystem health, but at
	least it indicates landscape level change.

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
	surface water change.

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

st.plotly_chart(fig, use_container_width=True)

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

	3. Fires (count per month) whole line

	4. Fire anomalies

	5. Human modifcation (histogram for 2019)

	6. Land cover

	7. Evapotranspiration

	8. Surface water


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

