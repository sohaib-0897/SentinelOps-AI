import {notFound} from "next/navigation";
import {ResourceView} from "@/components/resource-view";
const sections: Record<string,string> = {services:"Services",metrics:"Metrics",deployments:"Deployments",postmortems:"Postmortems",system:"System status"};
export default async function Page({params}: {params: Promise<{section: string}>}) {const {section} = await params; const title = sections[section]; if (!title) notFound(); return <ResourceView section={title}/>;}
