interface DialectStampProps {
  stamp: string;
}

export function DialectStamp({ stamp }: DialectStampProps) {
  return <p className="dialect-stamp">{stamp}</p>;
}
