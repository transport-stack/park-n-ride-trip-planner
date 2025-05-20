## SETUP

```bash
git clone https://gitlab.com/chartrmobility/directions

cd directions

virtualenv venv
source venv/bin/activate

pip install -r requirements.txt
```

now download static files from cloud or copy your own copy
```
curl https://static-02.sgp1.digitaloceanspaces.com/directions-files/zero_hop.7z --output static/meta/zero_hop.7z
=======
## SETUP

```bash
git clone https://gitlab.com/chartrmobility/directions

cd directions

virtualenv venv
source venv/bin/activate

pip install -r requirements.txt
```

Add the static folder in root directory. Ask admin for static folder zip file.

### End points for directions
1. Static Bus Directions (Zero-Hop + One-Hop):
```
/get_directions_bus?src=SOURCE&dest=DESTINATION&time=TIME
```
Path:
```
bus/algo/static_result.py
```
2. Metro Directions (All)
```
/get_directions_metro?src=SOURCE&dest=DESTINATION&time=TIME
```
Path:
```
metro/algo/k_shortest.py
```