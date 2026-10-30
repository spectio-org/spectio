import { createContext, useContext } from "react";
import type { ServerVersion } from "./api";

/** The server's `GET /version`, read once by the shell; null until it answers. */
export const ServerContext = createContext<ServerVersion | null>(null);
export const useServer = () => useContext(ServerContext);
