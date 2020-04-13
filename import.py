import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for ISBN,title,author,pub_year in reader:

        db.execute("INSERT INTO books (isbn,title,author,pubyr) VALUES (:ISBN, :title, :author,:pub_year)",
                    {"ISBN": ISBN, "title": title, "author": author,"pub_year": pub_year})
        print(f"Added book  {ISBN},{title},{author},{pub_year}.")
    db.commit()

if __name__ == "__main__":
    main()
