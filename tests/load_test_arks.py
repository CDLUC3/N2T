import typing
import duckdb

def get_dbcn():
    dbcn = duckdb.connect()
    dbcn.sql("INSTALL mysql;")
    dbcn.sql("attach 'host=127.0.0.1 user=ezidro port=3310 database=ezid' as ezid (type mysql);")
    dbcn.sql("USE ezid;")
    return dbcn


def get_naans(dbcn)->typing.List[str]:
    naans = []
    dbcn.execute("SELECT prefix FROM ezidapp_shoulder WHERE type='ARK';")
    for row in dbcn.fetchall():
        parts = row[0].split("/")
        naan = parts[1]
        if naan not in naans:
            naans.append(naan)
    naans.sort()
    return naans


def main():
    dbcn = get_dbcn()
    naans = get_naans(dbcn)
    arks = []
    for naan in naans:
        print(naan)
        dbcn.execute("SELECT identifier,target FROM ezidapp_identifier WHERE identifier LIKE 'ARK:/'")


if __name__ == "__main__":
    main()