-- Create a database
create database company;

-- Use company database
use company;

-- Create a table
CREATE TABLE software_developer(
    id INT AUTO_INCREMENT PRIMARY KEY,
    emp_id VARCHAR(10) UNIQUE,
    profile_photo VARCHAR(255),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    password varchar(255) not null,
    department VARCHAR(100) not null,
    job_role VARCHAR(50) NOT NULL,
    status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Inactive',
    joined_date DATE NOT NULL,
    gender VARCHAR (20),
    marital_status VARCHAR (30),
    salary INT,
    mobile VARCHAR (20),
    date_of_birth DATE,
    skill_set VARCHAR (255),
    street VARCHAR (150),
    city VARCHAR (100),
    state VARCHAR (100),
    zip VARCHAR (50),
    country VARCHAR (50),
    login_time TIMESTAMP,
	logout_time TIMESTAMP,
	session_token VARCHAR(255),
    message VARCHAR (50)
);