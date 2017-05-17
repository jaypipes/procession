-- +goose Up
-- SQL in section 'Up' is executed when this migration is applied

CREATE TABLE IF NOT EXISTS organization_users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY
, organization_id INT UNSIGNED NOT NULL
, user_id INT UNSIGNED NOT NULL
, UNIQUE INDEX uix_organization_user (organization_id, user_id)
, INDEX ix_user_organization (user_id, organization_id)
);

-- +goose Down
-- SQL section 'Down' is executed when this migration is rolled back
