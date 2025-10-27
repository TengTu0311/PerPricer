
We describe how to construct the existence and cardinality inference attacks over existing query pricing studies (i.e.,  PBP and IBP) on the MySQL database server.
This README provides instructions on how to set up and run the default experiments, including data preparation, environment setup, and execution of experiments. 

# Environment setup  \&  Data preparation

## Environment setup

Before running any experiments, ensure your environment is correctly set up. This project requires:
- Python: 3.7
- MySQL Server (8.0 or newer)
- Necessary libraries:
  - Mysql
  - Mysql-connector-python
  - Mysqlclient
  - Pymysql
  - Pandas
  - Sqlglot
  - sqlalchemy
  - ortools 
All libraries are provided in the `requirements.txt`.
Make sure Python, MySQL, and other libraries are properly installed and configured on your system. It's also recommended to create a virtual environment for Python dependencies to avoid any conflicts with other projects.

## Data preparation

There are four datasets used in the experiments:
- [Walmart](https://aws.amazon.com/marketplace/pp/prodview-zaejml2253r7k)
- [Employment](https://aws.amazon.com/marketplace/pp/prodview-yp5x2esst5dji#offers)
- [TPC-H](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)
- [SSB](https://github.com/eyalroz/ssb-dbgen)

The `sql` files of the first two datasets are provided, which can be used to directly import the database to mysql via the following codes.
```
mysql -u username -p walmart < walmart.sql
mysql -u username -p employment < employment.sql
```
For the other datasets (TPC-H, and SSB), follow the instructions on their respective websites to generate the datasets and import them (i.e., `tpch1g` and `ssb1g`) into MySQL.


# Reproduce the experiments 


## Run from scratch (Data have been prepared well)
1. Replace the `user` the `password` with your username and password of MySQL in the `dbSettings.py`
2. Generate the support sets (i.e.,  the possible databases) for the information-based pricing work `IBP` by runing the codes.
```bash
python qa_generate_db.py
```
The generated support sets are automatically imported into the database.

3. Run the codes to generate the values whose existence and cardinality to be checked and obtain the prices of corresponding queries. The generation results are in the `test_values` folder and the price files are in `attack_pre_rs` folder.
```bash
python generate_checked_values.py
```

4. Run the following codes and the corresponding results are in the `attack_rs` folder.
```bash
python attacker.py
```
