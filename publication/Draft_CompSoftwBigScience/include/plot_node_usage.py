import csv
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib

font = {'family' : 'normal',
        'size'   : 13}

matplotlib.rc('font', **font)

read_file = open("vre-usage-nemo.csv")
csvf      = csv.reader(read_file)

months       = []
bare_metals  = []
vres         = []
shareholders = []

for l in csvf:
    if not l[0].startswith('2'): continue

    month         = dt.datetime.strptime(l[0],"%Y-%m")
    bmns          = float(l[1])
    vrens         = float(l[2])
    shareholderns = float(l[3])

    total     = vrens+bmns
    vrens_rel = vrens/total
    bmns_rel  = bmns/total
    months.append       (month        )
    bare_metals.append  (bmns_rel     )
    vres.append         (vrens_rel    )
    shareholders.append (shareholderns)

time_axis = np.array(months)

print time_axis

vre_array = np.array(vres)
bm_array  = np.array(bare_metals)
sh_array  = np.array(shareholders)

width     = 31 #days
width     = 15 #days

vre_array = vre_array*100
bm_array  = bm_array*100

vre       = plt.bar(time_axis, vre_array,width, label="VRE Jobs")
bm        = plt.bar(time_axis, bm_array, width, bottom=vre_array,
                    label = "Bare-metal Jobs")

plt.ylabel("Cluster Usage (%)")
plt.xlabel("Month")
print plt.xticks()

plt.yticks(np.arange(0, 101, 10))

plt.xticks( time_axis[::2] )
fig = plt.gcf().autofmt_xdate()

plt.legend()

plt.savefig('../figures/NodeUsage_2016-09_2018-09.pdf',dpi=400)
plt.show()
raw_input()
plt.close()
