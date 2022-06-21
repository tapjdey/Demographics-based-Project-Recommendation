import streamlit as st
import json
import urllib
from collections import Counter
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from bokeh.models import ColumnDataSource
from bokeh.models import DataTable, TableColumn, HTMLTemplateFormatter

def show_table(project_and_count, no_project):
    df = pd.DataFrame( {
        'Project Link': [x[0] for x in project_and_count.most_common(no_project)],
        'Contributor Count' : [x[1] for x in project_and_count.most_common(no_project)],
        'Rank' : range(1,len(project_and_count.most_common(no_project))+1)
    })
    cds = ColumnDataSource(df)
    columns = [
    TableColumn(field="Project Link", title="Project Link", 
    formatter=HTMLTemplateFormatter(template='<a href="<%= value %>"target="_blank"><%= value %>')),
    TableColumn(field="Contributor Count", title="Contributor Count"),
    TableColumn(field="Rank", title="Rank")
    ]
    # columns.insert(1, "Rank")
    p = DataTable(source=cds, columns=columns, css_classes=["card"], index_position=None, 
    autosize_mode="fit_columns", syncable=False, width_policy='max', height=200, height_policy="auto")

    return(p)


def show_page():
    st.title('Location (TimeZone) based OSS Project Recommendation for Newcomers')
    with st.expander("See Details of what this app does:"):
        st.info("""
            Here we are showing the most popular projects (in terms of the number of contributors) in the user's Time Zone 
            and the nearby Time Zones (User's Time Zone ± 2 Hours). 
            We show two Tables - The top one with popular projects in the user's own Time Zone, 
            the bottom one with popular projects in nearby TimeZones.
        """)
        st.markdown("The source data is collected using the [World of Code](https://worldofcode.org/) dataset.")
    
    #define custom font size for tables
    st.markdown("""
    <style>
    .card {
    box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
    width: 100%;
    overflow: hidden;
    border-style: solid;
    border-color: #F0F0F0;
    border-width: thin;
    border-radius: 10px; /* 5px rounded corners */
    background-color: white;
    margin-bottom: 30px;
    font-size:15px !important;
    }
    .card-text {
        word-wrap: break-word;
        margin-left: 3rem;
    }
    .card:hover {
        box-shadow: 0 16px 32px 0 rgba(0,0,255,0.2);
        z-index: 2;
    -webkit-transition: all 200ms ease-in;
    -webkit-transform: scale(1.1);
    -ms-transition: all 200ms ease-in;
    -ms-transform: scale(1.1);
    -moz-transition: all 200ms ease-in;
    -moz-transform: scale(1.1);
    transition: all 200ms ease-in;
    transform: scale(1.1);
    }
    </style>
    """, unsafe_allow_html=True)

    # load relevant data
    with open('tz_project.json', 'r') as f:
        tzp_map = json.load(f)

    how = st.radio("Select How to get Your Location", ["Get My TimeZone Automatically", "I'll Select my TimeZone"], index=1,
                horizontal= True, help="We need your location for showing the project recommendations. Automatic TimeZone selection works best if you run the app yourself"
    )
    if how == "Get My TimeZone Automatically":
    # Try this
        try:
            # get geolocation
            with urllib.request.urlopen("https://geolocation-db.com/json") as url:
                data = json.loads(url.read().decode())
            
            # get timezone
            tf = TimezoneFinder()
            tzname = tf.timezone_at(lng=data['longitude'], lat=data['latitude'])
            utcoffset = datetime.now(ZoneInfo(tzname)).utcoffset()
            tzoffset = str(utcoffset.total_seconds()/3600.0)
            if float(tzoffset) < 0: 
                disptz = f"UTC-{str(timedelta(hours=-float(tzoffset)))[:-3]}"
            else:
                disptz = f"UTC+{utcoffset}"
            st.success(f'Your Automatically Detected Time Zone is: {disptz}')
        except:
            st.error('Unable to determine your location automatically! Please Input Your TimeZone!')
    
    elif how == "I'll Select my TimeZone":
        # list of available options
        tz_list = [f"UTC-{str(timedelta(hours=-float(x)))[:-3]}" if float(x)<0 else f"UTC+{str(timedelta(hours=float(x)))[:-3]}" for x in sorted(list(map(float, tzp_map.keys()))) ]
        tz_select = st.selectbox("Please Select Your Nearest TimeZone from this list", ['SELECT A TIMEZONE']+tz_list)
        
        if tz_select != 'SELECT A TIMEZONE':
            temptz = (tz_select.replace('UTC',''))[1:].split(':')
            tzoffset = str((float(temptz[0])+float(temptz[1])/60)*float(f"{(tz_select.replace('UTC',''))[0]}1") )
            if tzoffset == '0.0' :
                tzoffset = '0'
            st.success(f"Your Selected TimeZone is: {tz_select}")
        else:
            tzoffset = tz_select

    # get projects
    project_and_count = Counter()
    if tzoffset in tzp_map.keys():
        project_and_count += dict(tzp_map[tzoffset])

    # get projects for nearby timezones
        tzoffset_val = float(tzoffset)
        project_and_count_near = Counter()
        for key in tzp_map.keys():
            if key != tzoffset:
                key_val = float(key)
                if tzoffset_val - 2 <= key_val <= tzoffset_val +2 :
                    project_and_count_near += dict(tzp_map[key])

        # Select no. of recommendations
        no_project = st.slider('Select How Many Project Recommendations you wish to see:', min_value=1, max_value=20, value=5)

        # Table Explanantion
        with st.expander("See Table Explanation"):
            st.info('''The Contributor Counts show how many people have made a commit to the specific projects from the selected TimeZone, calculated using World of Code (WoC). 
                    It can be different (typically higher) than the contributor count on GitHub since the method of calculation is different, 
                    e.g., WoC counts the authors of rejected/pending Pull Requests as contributors, but GitHub doesn't.
            ''')
            st.info('''Since we did not use any fork-resolution, the projects might be a fork of another project, in which case, 
                    the user is recommeded to look into the source project. 
            ''')
            st.info('''For a few TimeZones, the maximum no. of projects available is less than 20, this could be becuase either there actually are
                    very few projects or because some of the popular projects have been deleted so our list got shorter during the regular link
                    availability checking (Please wait until the next update for fixes of such problems). 

            ''')
            st.info('''Unfortunately, some projects use fake commits to artificially inflate their community size. 
                    We do not filter for such cases here. This feature can be added later on depending on how World of Code tackles such issues.
            ''')
        # Timezone project
        p = show_table(project_and_count, no_project)
        st.header('Project Recommendation Table - Projects in your TimeZone (scrollable)')
        st.bokeh_chart(p)

        # Nearby project
        p_near = show_table(project_and_count_near, no_project)
        st.header('Project Recommendation Table - Projects in nearby TimeZones (scrollable)')
        st.bokeh_chart(p_near)

if __name__ == '__main__':
    st.set_page_config(page_title='Location-based OSS Project Prediction', layout="wide")
    show_page()
