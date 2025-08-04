from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)
    age = Column(Integer)
    role_id = Column(Integer, ForeignKey("roles.id"))
    is_active = Column(Boolean, default=True)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

class Color(Base):
    __tablename__ = "colors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

class Work(Base):
    __tablename__ = "works"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

class WorkAssignment(Base):
    __tablename__ = "work_assignments"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=True)
    color_id = Column(Integer, ForeignKey("colors.id"))
    person_id = Column(Integer, ForeignKey("persons.id"))
    description = Column(String, nullable=True)

class WorkAssignmentWork(Base):
    __tablename__ = "work_assignment_works"
    id = Column(Integer, primary_key=True, index=True)
    work_assignment_id = Column(Integer, ForeignKey("work_assignments.id"))
    work_id = Column(Integer, ForeignKey("works.id"))
    status = Column(Boolean, default=False)