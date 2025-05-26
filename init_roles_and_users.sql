--init_roles_and_users.sql
-- Crear rol configurador
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_configurador') THEN
        CREATE ROLE rol_configurador;
    END IF;
END $$;

-- Crear usuarios si no existen
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jvalero@udistrital.edu.co') THEN
        CREATE ROLE "jvalero@udistrital.edu.co" LOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jherrera@udistrital.edu.co') THEN
        CREATE ROLE "jherrera@udistrital.edu.co" LOGIN;
    END IF;
END $$;

-- Conceder permiso explícito de lectura sobre roles
GRANT SELECT ON pg_roles TO "jvalero@udistrital.edu.co";
GRANT SELECT ON pg_roles TO "jherrera@udistrital.edu.co";

-- Asignar rol configurador
GRANT rol_configurador TO "jvalero@udistrital.edu.co";
GRANT rol_configurador TO "jherrera@udistrital.edu.co";
