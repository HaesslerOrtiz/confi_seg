--init_roles_and_users.sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_configurador') THEN
        CREATE ROLE rol_configurador LOGIN;
    END IF;
    /*
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_lider') THEN
        CREATE ROLE rol_lider LOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_tutor') THEN
        CREATE ROLE rol_tutor LOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_estudiante') THEN
        CREATE ROLE rol_estudiante LOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rol_contribuyente') THEN
        CREATE ROLE rol_contribuidor LOGIN;
    END IF;*/
END
$$;

-- Crear usuarios base con rol de configurador
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
