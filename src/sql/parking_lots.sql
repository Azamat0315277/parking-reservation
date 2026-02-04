-- ============================================================================
-- STARGATE PARKING FACILITY - Database Schema
-- ============================================================================

CREATE SCHEMA parking;

-- Drop table if exists (optional - uncomment if needed)
DROP TABLE IF EXISTS parking.parking_lots;

-- ============================================================================
-- TABLE DEFINITION
-- ============================================================================

CREATE TABLE parking.parking_lots (
    parking_id INT PRIMARY KEY,
    parking_type VARCHAR(50) NOT NULL,
    space_availability BOOLEAN DEFAULT TRUE,
    reservation_start TIMESTAMP NULL,
    reservation_end TIMESTAMP NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- ============================================================================
-- PARKING TYPE DISTRIBUTION (100 spots total):
--   Spots 1-15:   Premium (Level 1)      - $6.00/hour
--   Spots 16-65:  Standard (Levels 2-5)  - $4.00/hour
--   Spots 66-85:  Rooftop (Level 6)      - $3.00/hour
--   Spots 86-95:  Oversized              - $7.00/hour
--   Spots 96-100: Motorcycle             - $2.00/hour
-- ============================================================================

-- ============================================================================
-- PREMIUM PARKING SPOTS (Level 1) - $6.00/hour
-- Spots 1-15
-- ============================================================================

INSERT INTO parking.parking_lots (parking_id, parking_type, space_availability, reservation_start, reservation_end, price) VALUES
(1,  'Premium',    FALSE, '2026-01-20 08:00:00', '2026-01-20 17:00:00', 6.00),
(2,  'Premium',    FALSE, '2026-01-20 07:30:00', '2026-01-20 18:30:00', 6.00),
(3,  'Premium',    TRUE,  NULL, NULL, 6.00),
(4,  'Premium',    FALSE, '2026-01-20 09:15:00', '2026-01-20 14:00:00', 6.00),
(5,  'Premium',    TRUE,  NULL, NULL, 6.00),
(6,  'Premium',    FALSE, '2026-01-20 06:45:00', '2026-01-20 19:00:00', 6.00),
(7,  'Premium',    FALSE, '2026-01-20 10:00:00', '2026-01-20 16:00:00', 6.00),
(8,  'Premium',    TRUE,  NULL, NULL, 6.00),
(9,  'Premium',    FALSE, '2026-01-20 08:30:00', '2026-01-20 12:30:00', 6.00),
(10, 'Premium',    TRUE,  NULL, NULL, 6.00),
(11, 'Premium',    FALSE, '2026-01-20 07:00:00', '2026-01-20 20:00:00', 6.00),
(12, 'Premium',    FALSE, '2026-01-20 11:00:00', '2026-01-20 15:00:00', 6.00),
(13, 'Premium',    TRUE,  NULL, NULL, 6.00),
(14, 'Premium',    FALSE, '2026-01-20 09:00:00', '2026-01-20 17:30:00', 6.00),
(15, 'Premium',    TRUE,  NULL, NULL, 6.00);

-- ============================================================================
-- STANDARD PARKING SPOTS (Levels 2-5) - $4.00/hour
-- Spots 16-65
-- ============================================================================

INSERT INTO parking.parking_lots (parking_id, parking_type, space_availability, reservation_start, reservation_end, price) VALUES
(16, 'Standard',   FALSE, '2026-01-20 08:00:00', '2026-01-20 17:00:00', 4.00),
(17, 'Standard',   TRUE,  NULL, NULL, 4.00),
(18, 'Standard',   FALSE, '2026-01-20 07:45:00', '2026-01-20 16:30:00', 4.00),
(19, 'Standard',   FALSE, '2026-01-20 09:00:00', '2026-01-20 18:00:00', 4.00),
(20, 'Standard',   TRUE,  NULL, NULL, 4.00),
(21, 'Standard',   TRUE,  NULL, NULL, 4.00),
(22, 'Standard',   FALSE, '2026-01-20 06:30:00', '2026-01-20 15:00:00', 4.00),
(23, 'Standard',   FALSE, '2026-01-20 10:30:00', '2026-01-20 14:30:00', 4.00),
(24, 'Standard',   TRUE,  NULL, NULL, 4.00),
(25, 'Standard',   FALSE, '2026-01-20 08:15:00', '2026-01-20 17:15:00', 4.00),
(26, 'Standard',   TRUE,  NULL, NULL, 4.00),
(27, 'Standard',   FALSE, '2026-01-20 07:00:00', '2026-01-20 19:00:00', 4.00),
(28, 'Standard',   FALSE, '2026-01-20 09:30:00', '2026-01-20 13:00:00', 4.00),
(29, 'Standard',   TRUE,  NULL, NULL, 4.00),
(30, 'Standard',   TRUE,  NULL, NULL, 4.00),
(31, 'Standard',   FALSE, '2026-01-20 08:00:00', '2026-01-20 16:00:00', 4.00),
(32, 'Standard',   FALSE, '2026-01-20 11:00:00', '2026-01-20 20:00:00', 4.00),
(33, 'Standard',   TRUE,  NULL, NULL, 4.00),
(34, 'Standard',   FALSE, '2026-01-20 07:30:00', '2026-01-20 18:00:00', 4.00),
(35, 'Standard',   TRUE,  NULL, NULL, 4.00),
(36, 'Standard',   FALSE, '2026-01-20 09:00:00', '2026-01-20 15:30:00', 4.00),
(37, 'Standard',   TRUE,  NULL, NULL, 4.00),
(38, 'Standard',   FALSE, '2026-01-20 06:00:00', '2026-01-20 14:00:00', 4.00),
(39, 'Standard',   FALSE, '2026-01-20 10:00:00', '2026-01-20 17:00:00', 4.00),
(40, 'Standard',   TRUE,  NULL, NULL, 4.00),
(41, 'Standard',   TRUE,  NULL, NULL, 4.00),
(42, 'Standard',   FALSE, '2026-01-20 08:45:00', '2026-01-20 16:45:00', 4.00),
(43, 'Standard',   FALSE, '2026-01-20 07:15:00', '2026-01-20 19:30:00', 4.00),
(44, 'Standard',   TRUE,  NULL, NULL, 4.00),
(45, 'Standard',   FALSE, '2026-01-20 09:00:00', '2026-01-20 12:00:00', 4.00),
(46, 'Standard',   TRUE,  NULL, NULL, 4.00),
(47, 'Standard',   FALSE, '2026-01-20 08:30:00', '2026-01-20 18:30:00', 4.00),
(48, 'Standard',   TRUE,  NULL, NULL, 4.00),
(49, 'Standard',   FALSE, '2026-01-20 10:15:00', '2026-01-20 15:15:00', 4.00),
(50, 'Standard',   FALSE, '2026-01-20 07:00:00', '2026-01-20 17:00:00', 4.00),
(51, 'Standard',   TRUE,  NULL, NULL, 4.00),
(52, 'Standard',   TRUE,  NULL, NULL, 4.00),
(53, 'Standard',   FALSE, '2026-01-20 08:00:00', '2026-01-20 20:00:00', 4.00),
(54, 'Standard',   FALSE, '2026-01-20 09:30:00', '2026-01-20 14:00:00', 4.00),
(55, 'Standard',   TRUE,  NULL, NULL, 4.00),
(56, 'Standard',   FALSE, '2026-01-20 06:45:00', '2026-01-20 16:00:00', 4.00),
(57, 'Standard',   TRUE,  NULL, NULL, 4.00),
(58, 'Standard',   FALSE, '2026-01-20 11:30:00', '2026-01-20 19:00:00', 4.00),
(59, 'Standard',   FALSE, '2026-01-20 08:00:00', '2026-01-20 13:30:00', 4.00),
(60, 'Standard',   TRUE,  NULL, NULL, 4.00),
(61, 'Standard',   TRUE,  NULL, NULL, 4.00),
(62, 'Standard',   FALSE, '2026-01-20 07:30:00', '2026-01-20 17:30:00', 4.00),
(63, 'Standard',   FALSE, '2026-01-20 09:00:00', '2026-01-20 18:00:00', 4.00),
(64, 'Standard',   TRUE,  NULL, NULL, 4.00),
(65, 'Standard',   FALSE, '2026-01-20 10:00:00', '2026-01-20 16:00:00', 4.00);

-- ============================================================================
-- ROOFTOP PARKING SPOTS (Level 6 - Uncovered) - $3.00/hour
-- Spots 66-85
-- ============================================================================

INSERT INTO parking.parking_lots (parking_id, parking_type, space_availability, reservation_start, reservation_end, price) VALUES
(66, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(67, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(68, 'Rooftop',    FALSE, '2026-01-20 08:00:00', '2026-01-20 17:00:00', 3.00),
(69, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(70, 'Rooftop',    FALSE, '2026-01-20 07:00:00', '2026-01-20 19:00:00', 3.00),
(71, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(72, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(73, 'Rooftop',    FALSE, '2026-01-20 09:30:00', '2026-01-20 15:00:00', 3.00),
(74, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(75, 'Rooftop',    FALSE, '2026-01-20 06:30:00', '2026-01-20 14:30:00', 3.00),
(76, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(77, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(78, 'Rooftop',    FALSE, '2026-01-20 10:00:00', '2026-01-20 18:00:00', 3.00),
(79, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(80, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(81, 'Rooftop',    FALSE, '2026-01-20 08:30:00', '2026-01-20 16:30:00', 3.00),
(82, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(83, 'Rooftop',    TRUE,  NULL, NULL, 3.00),
(84, 'Rooftop',    FALSE, '2026-01-20 11:00:00', '2026-01-20 20:00:00', 3.00),
(85, 'Rooftop',    TRUE,  NULL, NULL, 3.00);

-- ============================================================================
-- OVERSIZED VEHICLE SPOTS - $7.00/hour
-- Spots 86-95
-- ============================================================================

INSERT INTO parking.parking_lots (parking_id, parking_type, space_availability, reservation_start, reservation_end, price) VALUES
(86, 'Oversized',  FALSE, '2026-01-20 07:00:00', '2026-01-20 18:00:00', 7.00),
(87, 'Oversized',  TRUE,  NULL, NULL, 7.00),
(88, 'Oversized',  FALSE, '2026-01-20 08:30:00', '2026-01-20 17:30:00', 7.00),
(89, 'Oversized',  TRUE,  NULL, NULL, 7.00),
(90, 'Oversized',  TRUE,  NULL, NULL, 7.00),
(91, 'Oversized',  FALSE, '2026-01-20 09:00:00', '2026-01-20 15:00:00', 7.00),
(92, 'Oversized',  TRUE,  NULL, NULL, 7.00),
(93, 'Oversized',  FALSE, '2026-01-20 06:00:00', '2026-01-20 19:00:00', 7.00),
(94, 'Oversized',  TRUE,  NULL, NULL, 7.00),
(95, 'Oversized',  TRUE,  NULL, NULL, 7.00);

-- ============================================================================
-- MOTORCYCLE SPOTS - $2.00/hour
-- Spots 96-100
-- ============================================================================

INSERT INTO parking.parking_lots (parking_id, parking_type, space_availability, reservation_start, reservation_end, price) VALUES
(96, 'Motorcycle', FALSE, '2026-01-20 08:00:00', '2026-01-20 17:00:00', 2.00),
(97, 'Motorcycle', TRUE,  NULL, NULL, 2.00),
(98, 'Motorcycle', TRUE,  NULL, NULL, 2.00),
(99, 'Motorcycle', FALSE, '2026-01-20 09:00:00', '2026-01-20 18:00:00', 2.00),
(100,'Motorcycle', TRUE,  NULL, NULL, 2.00);

