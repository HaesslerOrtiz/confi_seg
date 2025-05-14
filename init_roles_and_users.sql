--init_roles_and_users.sql
-- Crear rol configurador
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_configurador') THEN
        CREATE ROLE rol_configurador;
    END IF;

    /*
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_lider') THEN
        CREATE ROLE rol_lider;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_tutor') THEN
        CREATE ROLE rol_tutor;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_estudiante') THEN
        CREATE ROLE rol_estudiante;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_contribuidor') THEN
        CREATE ROLE rol_contribuidor;
    END IF;
    */
END
$$;

-- Crear usuarios con rol_configurador
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jvalero@udistrital.edu.co') THEN
        CREATE ROLE "jvalero@udistrital.edu.co" LOGIN IN ROLE rol_configurador;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jherrera@udistrital.edu.co') THEN
        CREATE ROLE "jherrera@udistrital.edu.co" LOGIN IN ROLE rol_configurador;
    END IF;
END
$$;

-- Conceder permiso de lectura sobre pg_roles
GRANT SELECT ON pg_roles TO "jvalero@udistrital.edu.co";
GRANT SELECT ON pg_roles TO "jherrera@udistrital.edu.co";