from models import db, Contact, User
from faker import Factory

fake = Factory.create()
db.drop_all()
db.create_all()
# Make 100 fake contacts
for num in range(100):
    fullname = fake.name().split()
    name = fullname[0]
    surname = ' '.join(fullname[1:])
    email = fake.email()
    phone = fake.phone_number()
    # Save in database
    my_contact = Contact(name=name, surname=surname, email=email, phone=phone)
    db.session.add(my_contact)

db.session.commit()

username = "Nishesh"
password = "plivo"
user = User(username=username)
user.hash_password(password)
db.session.add(user)
db.session.commit()

username = "Bharech"
password = "plivo"
user = User(username=username)
user.hash_password(password)
db.session.add(user)
db.session.commit()
