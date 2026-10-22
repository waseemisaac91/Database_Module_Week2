
-- Author: Waseem
-- Database_Module_Week2  
--Assigment-1
-- Description: Queries for the Rental Database (Sakila)
-- ==========================================

-- 1. Show the first and last names of actors whose first names are Nick, Ed, or Jennifer.
SELECT first_name, last_name 
FROM actor
WHERE first_name IN ('Nick', 'Ed', 'Jennifer');


-- 2. Show only the last name of actors whose first names are Ed, Nick, or Jennifer.
SELECT last_name 
FROM actor
WHERE first_name IN ('Nick', 'Ed', 'Jennifer');


-- 3. Show all details from the address table.
SELECT * 
FROM address;


-- 4. Display district and phone from the address table, sorted in descending order.
-- Note: NULLS LAST ensures empty districts appear at the end (PostgreSQL specific).
SELECT district, phone 
FROM address 
ORDER BY district DESC NULLS LAST;


-- 5. Using film_id from the film and inventory tables, show film_id, title from the film table, and inventory_id from the inventory table.
SELECT f.film_id, f.title, i.inventory_id 
FROM film f 
JOIN inventory i ON f.film_id = i.film_id;


-- 6. Show the first 5 rows consisting of the inventory and rental tables.
SELECT * 
FROM inventory i 
JOIN rental r ON i.inventory_id = r.inventory_id
LIMIT 5;


-- 7. Show the first 10 rows consisting of rental_id, rental_date, and payment_id from the rental and payment tables, ordered by amount in descending order.
SELECT r.rental_id, r.rental_date, p.payment_id 
FROM rental r 
JOIN payment p ON r.rental_id = p.rental_id
ORDER BY p.amount DESC
LIMIT 10;


-- 8. Show all details of rows where actor_id is empty (NULL) in the actor table.
SELECT * 
FROM actor 
WHERE actor_id IS NULL;


-- 9. Show all details of rows in the actor table where actor_id is not empty (NOT NULL).
SELECT * 
FROM actor 
WHERE actor_id IS NOT NULL;


-- 10. Find the number of non-empty rows in the film table.
SELECT COUNT(film_id) 
FROM film;


-- 11. Show the total amount from the payment table as the output header sum_amt.
SELECT SUM(amount) AS sum_amt 
FROM payment;


-- 12. Show the maximum and minimum amount in the payment table.
SELECT MAX(amount) AS max_amount, MIN(amount) AS min_amount 
FROM payment;