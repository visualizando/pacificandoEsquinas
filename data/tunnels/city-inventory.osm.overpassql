[out:json][timeout:180];
area["ISO3166-2"="AR-C"]["boundary"="administrative"]->.city;
(way(area.city)[highway][tunnel][tunnel!="no"];way(area.city)[railway=rail];);
out geom;