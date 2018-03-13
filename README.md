# eGymInscriptions

### facultatif: 
```
virtualenv monprojet
cd monprojet
source bin/activate
```

### obligatoire
```
pip install lxml paramiko
pip install git+https://github.com/jeremie-borel/PyFileMaker.git
git clone https://github.com/jeremie-borel/eGymInscriptions
```

### déclencher le script:
```
cd eGymInscriptions
python parser_einscriptions.py
```

### Parser les factures
La lecture du fichier xl demande le paquet openpyxl.

