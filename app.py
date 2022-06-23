from numpy import rec
import streamlit as st
import json
import urllib
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from bokeh.models import DataTable, TableColumn, HTMLTemplateFormatter, ColumnDataSource

def show_table(PCgtzCatzCggCagMFtzMFg, colnames):
    
    df = pd.DataFrame(PCgtzCatzCggCagMFtzMFg, columns=colnames)
    df['Rank'] =  range(1,len(PCgtzCatzCggCagMFtzMFg)+1)
    # print(df)
    cds = ColumnDataSource(df)
    columns = [
    TableColumn(field=colnames[x], title=colnames[x], 
    formatter=HTMLTemplateFormatter(template='<a href="<%= value %>"target="_blank"><%= value %>')) if x ==0 else \
        TableColumn(field=colnames[x], title=colnames[x]) for x in range(len(colnames))
    ]+[TableColumn(field="Rank", title="Rank")]

    p = DataTable(source=cds, columns=columns, css_classes=["card"], index_position=None,
    autosize_mode="fit_columns", syncable=False, width_policy='max', height=200, height_policy="auto")

    return(p)

def filter_table(is_diversity, diversity_value, diversity_option, data, tzoffset, gender,no_project ):
    if is_diversity:
        min_mf_ratio = (100 - diversity_value[1])/diversity_value[1]
        max_mf_ratio = (100 - diversity_value[0])/diversity_value[0]
        rec_table = []
        if diversity_option == 'Local Diversity':
            listindex = -2
        else:
            listindex = -1
        # print(min_mf_ratio, max_mf_ratio)
        for item in data[tzoffset][gender]:
            if min_mf_ratio <= float(item[listindex]) <= max_mf_ratio:
                rec_table.append(item) 
    else:
        rec_table = data[tzoffset][gender]
    if len(rec_table) > no_project:
        rec_table = rec_table[:no_project]

    return(rec_table)

def show_page():
    st.title('Demographic-based Project Recommendation for OSS Newcomers')
    with st.expander("See Details of what this app does:"):
        st.info("""
            Our goal is to show the most popular projects (in terms of the number of contributors) to the user based on their 
            Time Zone and Gender preferences. Users can also choose to see the more Gender-Diverse projects based on their preference.""")
        st.info("""    
            We are showing the popular projects in the user's Time Zone or Globally based on their choice.
            Optionally, we can show the popular projects in nearby Time Zones (User's Time Zone ± 2 Hours). 
        """)
        st.info( """
            We can also show projects based on the user's gender preference or across all genders as per their choice.
        """)
        st.markdown("The source data is collected using the [World of Code](https://worldofcode.org/) (WoC) dataset.")
        st.warning(
            """DISCLAIMER! We fully support people who do not identify with either of the two binary genders, 
            the reason for showing only two genders here is because WoC only identifies people as male or female 
            (or 'Unknown' for developers who do not provide a common name)."""
        )

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
    font-size:9.5px !important;
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
    # tz : gender: [url, tz_count_gender, tz_count_all, global_count_gender, global_count_all, mf_ratio_tz, mf_ratio_global]
    with open('tz_project_gender.json', 'r') as f:
        data = json.load(f)
        data_global = {'global':data.pop('global')}

    # Define input option dicts - makes easier to reference
    tz_option = {'I want to select my Time Zone':'s_tz', 'Show me the Global Results': 's_g',
     "Get my Time Zone Automatically **(only works if you're hosting the app yourself!)**": 'a_tz'}

    gender_option = {'Show me Projects Popular among Male Developers': 'male',
    'Show me Projects Popular among Female Developers': 'female', 'Show me Projects Popular among all Developers': 'all'}

    # TZ selection
    tz_selection = st.radio("Select How to get Your Location", tz_option.keys(),
                horizontal= True
    ) 

    if tz_option[tz_selection] == "a_tz":
    # Automatic Geolocation --- only runs on server side
        try:
            # get geolocation
            with urllib.request.urlopen("https://geolocation-db.com/json") as url:
                locdata = json.loads(url.read().decode())
            
            # get timezone
            tf = TimezoneFinder()
            tzname = tf.timezone_at(lng=locdata['longitude'], lat=locdata['latitude'])
            utcoffset = datetime.now(ZoneInfo(tzname)).utcoffset()
            tzoffset = str(utcoffset.total_seconds()/3600.0)
            if float(tzoffset) < 0: 
                disptz = f"UTC-{str(timedelta(hours=-float(tzoffset)))[:-3]}"
            else:
                disptz = f"UTC+{utcoffset}"
            st.success(f'Your Automatically Detected Time Zone is: {disptz}')
        except:
            st.error('Unable to determine your location automatically! Please Input Your TimeZone!')
        nearby_select = st.checkbox('Show Projects in Nearby Time Zones')
    
    elif tz_option[tz_selection] == "s_tz":
        # list of available options
        tz_list = [f"UTC-{str(timedelta(hours=-float(x)))[:-3]}" if float(x)<0 else f"UTC+{str(timedelta(hours=float(x)))[:-3]}" \
            for x in sorted(list(map(float, data.keys()))) ]
        tz_select = st.selectbox("Please Select Your Nearest TimeZone from this list", ['SELECT A TIMEZONE']+tz_list)
        
        if tz_select != 'SELECT A TIMEZONE':
            temptz = (tz_select.replace('UTC',''))[1:].split(':')
            tzoffset = str((float(temptz[0])+float(temptz[1])/60)*float(f"{(tz_select.replace('UTC',''))[0]}1") )
            if tzoffset == '0.0' :
                tzoffset = '0'
            st.success(f"Your Selected TimeZone is: {tz_select}")
        else:
            tzoffset = tz_select
        nearby_select = st.checkbox('Show Projects in Nearby Time Zones')

    elif tz_option[tz_selection] == 's_g':
        st.success('OK! Showing you the global results. (Note: Nearby Time Zone project view disabled!)')
        tzoffset = 'global'
        nearby_select = False

    # gender selection
    gender_select = st.radio("Do you want to see projects popular among people of specific gender?", gender_option.keys(),
                horizontal= False, index=2)

    # diversity
    is_diversity = st.checkbox("Diversity Filter: Do you want to see projects with certain percentage of female developers?")
    diversity_value = diversity_option = 0
    if is_diversity:
        diversity_option = st.radio("Do you want to Filter by Diversity Locally (in your Time Zone) or Globally?",
        ['Local Diversity', 'Global Diversity'] ,horizontal=True, 
        help='Diversity can be calculated among the developers in your Time Zone who contributed to a project (Local Diversity) or \
            among all developers globally (Global Diversity). Choose which value of diversity you want to filter by.')
        diversity_value = st.slider("Select a range of values: (percentage of female developers)", 1, 100, (10,50)) # two values

    # no. of recommendations
    no_project = st.slider('Select How Many Project Recommendations you wish to see:', min_value=1, max_value=20, value=5)

    # show project table: 
    # Table Explanantion
    with st.expander("See Table Explanation"):
            st.info('''The Contributor Counts show how many people have made a commit to the specific projects from the selected TimeZone, calculated using World of Code (WoC). 
                    It can be different than the contributor count on GitHub since the method of calculation is different.
            ''')
            st.info('''Since we did not use any fork-resolution, the projects might be a fork of another project, in which case, 
                    the user is recommeded to look into the source project. 
            ''')
            st.info('''For a few TimeZones, the maximum no. of projects available is less than 20, this could be becuase either there actually are
                    very few projects or because some of the popular projects have been deleted so our list got shorter during the regular link
                    availability checking (Please wait until the next update for fixes of such problems). 
            ''')
            st.markdown("""
            Explanation of Table Columns (Not all columns maybe shown in the table depending on your selections):
            1. `Project URL` : URL of the recommended project.
            2. `Dev.Count:Selected TZ & Gender`: No. of contributors to the projects from your selected Time Zone & Gender.
            3. `Dev.Count:Selected TZ, All Gender`: No. of contributors to the projects from your selected Time Zone for all genders.
            4. `Dev.Count:Global,Selected Gender`: No. of contributors to the projects globally for your selected gender.
            5. `Dev.Count: Global & All Gender`: No. of contributors to the projects globally for all genders.
            6. `Female Dev.:Local`: Percentage of Female Developers among contributors to the project from selected Time Zone.
            7. `Female Dev.:Global`: Percentage of Female Developers among contributors to the project globally.
            8. `Rank`: Rank of the project (sorted by column 2).

            **Additionally, the Tables are Interactive and can be SORTED by any of the columns - _just click on the column header!_**
            """)

    gender = gender_option[gender_select]
    colnames = ['Project URL', 'Dev.Count:Selected TZ & Gender', 'Dev.Count:Selected TZ, All Gender',\
            'Dev.Count:Global,Selected Gender', 'Dev.Count: Global & All Gender',\
            'Female Dev.:Local', 'Female Dev.:Global' ]

    if tzoffset in data.keys():
        # filter table by diversity
        rec_table = filter_table(is_diversity, diversity_value, diversity_option, data, tzoffset, gender,no_project )
        fil_table = []
        if gender == 'all':
            colnames = [e for i,e in enumerate(colnames) if i not in [1,3]]
            for te in rec_table:
                el = [e for i,e in enumerate(te) if i not in [1,3]]
                el[-2] = f'{100/(1+float(el[-2])):.2f}%'
                el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                fil_table.append(el)
        else:
            for el in rec_table:
                el[-2] = f'{100/(1+float(el[-2])):.2f}%'
                el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                fil_table.append(el)
        
        p = show_table(fil_table, colnames)
        # st.write(rec_table)
        st.header('Project Recommendation Table (scrollable)')
        st.bokeh_chart(p)

        # projects in nearby timezones
        if nearby_select:
            tzoffset_val = float(tzoffset)
            near_project = []
            for key in data.keys():
                if key != tzoffset:
                    key_val = float(key)
                    if tzoffset_val - 2 <= key_val <= tzoffset_val +2 :
                        near_project += filter_table(is_diversity, diversity_value, diversity_option, data, key, gender,no_project )
            if len(near_project) > no_project:
                near_project = near_project[:no_project]
            near_project.sort(key=lambda x: -x[1])
            fil_table_near = []
            if gender == 'all':
                for te in near_project:
                    el = [e for i,e in enumerate(te) if i not in [1,3]]
                    el[-2] = f'{100/(1+float(el[-2])):.2f}%'
                    el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                    fil_table_near.append(el)
            else:
                for el in near_project:
                    el[-2] = f'{100/(1+float(el[-2])):.2f}%'
                    el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                    fil_table_near.append(el)
            p_near = show_table(fil_table_near, colnames)
            # st.write(rec_table)
            st.header('Project Recommendation Table (scrollable)')
            st.bokeh_chart(p_near)


    elif tzoffset == 'global':
        # filter table by diversity
        rec_table = filter_table(is_diversity, diversity_value, diversity_option, data_global, tzoffset, gender,no_project )
        fil_table = []
        if gender == 'all':
            colnames = [e for i,e in enumerate(colnames) if i not in [1,2,3,5]]
            for te in rec_table:
                el = [e for i,e in enumerate(te) if i not in [1,2,3,5]]
                el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                fil_table.append(el)
        else:
            colnames = [e for i,e in enumerate(colnames) if i not in [1,2,5]]
            for te in rec_table:
                el = [e for i,e in enumerate(te) if i not in [1,2,5]]
                el[-1] = f'{100/(1+float(el[-1])):.2f}%'
                fil_table.append(el)
        p = show_table(fil_table, colnames)
        # st.write(fil_table)
        st.header('Project Recommendation Table (scrollable)')
        st.bokeh_chart(p)



if __name__ == '__main__':
    st.set_page_config(page_title='Demographic-based OSS Project Recommendation', layout="wide")
    show_page()

