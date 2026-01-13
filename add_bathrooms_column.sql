-- Add bathrooms column to price_data_model table if it doesn't exist
ALTER TABLE `price_data_model` 
ADD COLUMN IF NOT EXISTS `bathrooms` INT NOT NULL DEFAULT 2 AFTER `bedrooms`;
